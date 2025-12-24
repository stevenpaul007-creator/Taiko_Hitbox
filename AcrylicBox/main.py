import FreeCAD as App
import Part
import math
import Draft
import importDXF  # 专门负责 DWG 导出的模块
import os

Gui.runCommand('Std_CloseAllWindows',0)

# 顶层覆盖板螺丝孔是否需要沉头 部分厂商不支持沉头
CSK_ENABLE = False

EXPORT_DXF_ENABLE = True
EXPORT_DXF_FOLDER = "d:/temp/export" 

# --- 1. 参数定义 (单位: mm) ---
L = 200.0  # 长度 (X)
W = 100.0  # 宽度 (Y)
T = 3.0    # 亚克力厚度
T_COVER = 2.0   # 面板厚度
SUPPORT_H = 40  # 支撑高度
H = SUPPORT_H + 2*T + T_COVER   # 总高度 (Z)

M3_HOLE = 3.2  # M3螺丝孔径 (略大一点方便穿过)

# 按键参数
MAIN_D = 24.0      # 主按键直径
FUNC_D = 12.0      # 功能键直径
SLOT_W = T         # 榫槽宽度即板厚
SLOT_L = 20.0      # 榫槽长度

# 开孔公差
CUT_COMM = 0.2

# --- 2. 创建文档 ---
doc = App.newDocument("Taiko_Hitbox_Acrylic_Pro")

# --- 3. 核心布局坐标 ---
# 8个螺丝孔位置 (四角 + 四边中点)
screw_points = [
    (12, 12),      (L/2, 12 +6),     (L-12, 12),
    (12 + 6, W/2), (L/2, W/2+12),       (L-12 - 6, W/2),
    #              (L/2, W/2), 
    #(12, W-12),    (L/2, W-12 - 6),  (L-12, W-12)
    (12, W-12),                      (L-12, W-12)
]

# 沉头孔参数 (2025 标准 M3 螺丝)
CSK_D = 6.0    # 沉头直径 (通常为螺丝头直径+公差)
CSK_H = 1.2    # 沉头深度 (稍微深过 1mm 确保螺丝不刮手)

# 主按键位置
# 1左上, 2在1右下45度, 3在2右侧, 4在3右上和1同高
btn_L = (40, 55)                             # 左键
btn_D = (btn_L[0] + 30, btn_L[1] - 30)       # 下键
btn_A = (btn_D[0] + 60, btn_D[1])            # A键
btn_B = (btn_A[0] + 30, btn_L[1])            # B键
main_btns = [btn_L, btn_D, btn_A, btn_B]

# ////////////功能键位置///////////
# 定义功能键组的边距
S_GAP = 15.0 

# A. 左侧功能区
f_u = (btn_D[0] + S_GAP * 0.0, btn_D[1] + S_GAP * 2.8)
f_r = (  f_u[0] + S_GAP * 1.0,   f_u[1] - S_GAP * 1.0)

# B. 右侧功能区
f_y = (btn_A[0] + S_GAP * 0.0, btn_A[1] + S_GAP * 2.8)
f_x = (  f_y[0] - S_GAP * 1.0,   f_y[1] - S_GAP * 1.0)

# C. 中间 Start 键 (位于中心上方)
f_start = (L/2, W-23) 

# D. 底部 L/R 键 (放置在底部角落，避开横向支撑板)
f_lt = (23, W-23)
f_rt = (L - 23, W-23)

# 汇总 7 个功能键到列表中
func_btns = [f_u, f_r, f_x, f_y, f_start, f_lt, f_rt]
# ////////////功能键位置结束///////////


# 支撑板位置 (横向两条，避开按键)
support_x_positions = [L*0.2,  L/2, L*0.8]
support_y_positions = [10, W - 10]

# 支撑板位置 (纵向两条，避开按键)
# 纵向板 X 位置：放在螺丝孔内侧，比如 25mm 和 L-25mm
side_support_x = [10.0, L - 10.0]
# 纵向板上的榫头 Y 坐标：为了避开横向板，我们取中间位置
side_support_y_slots = [W/2] # 每侧 1 个大榫头，或 [W*0.3, W*0.7] 2个

# --- 4. 函数：创建带孔和槽的面板 ---
def create_main_panel(z_pos, mode="middle"):
    t = T
    if mode == "cover":
        t = T_COVER
    
    panel = Part.makeBox(L, W, t)
    
    # --- 新增：圆角处理 (R=10mm) ---
    radius = 10.0
    vertical_edges = []
    
    for edge in panel.Edges:
        # 1. 检查长度是否等于厚度 T
        # 2. 检查两个端点的 X 和 Y 是否一致（即垂直边）
        if abs(edge.Length - t) < 0.001:  # 长度匹配
            v1 = edge.Vertexes[0].Point
            v2 = edge.Vertexes[1].Point
            if abs(v1.x - v2.x) < 0.001 and abs(v1.y - v2.y) < 0.001:
                vertical_edges.append(edge)
    
    # 对筛选出的 4 条边应用圆角
    if len(vertical_edges) > 0:
        panel = panel.makeFillet(radius, vertical_edges)

    # 2. 处理螺丝孔 (所有模式都有螺丝孔，但 cover 模式有沉头)
    for p in screw_points:
        # 基础贯穿孔
        hole = Part.makeCylinder(M3_HOLE/2, t*2)
        hole.translate(App.Vector(p[0], p[1], -t/2))
        panel = panel.cut(hole)
        
        # 仅 cover 模式增加沉头处理
        if mode == "cover" and CSK_ENABLE:
            csk = Part.makeCylinder(CSK_D/2, CSK_H + 0.1) # 稍微加深一点避免精度缝隙
            csk.translate(App.Vector(p[0], p[1], t - CSK_H))
            panel = panel.cut(csk)
    # 3. 处理榫槽 (只有 middle 和 bottom 需要咬合支撑板)
    # 如果底层也不想要榫头外露，可以把 bottom 也排除
    if mode in ["middle", "bottom"]:
        # B.1 减去支撑板榫槽 (在面板上开槽)
        for sx in support_x_positions:
            for sy in support_y_positions:
                slot = Part.makeBox(SLOT_L + CUT_COMM, SLOT_W + CUT_COMM, T*2)
                slot.translate(App.Vector(sx - SLOT_L/2, sy - SLOT_W/2, -T/2))
                panel = panel.cut(slot)
    
        # B.2 增加纵向支撑板榫槽
        for sx in side_support_x:
            for sy in side_support_y_slots:
                # 纵向槽：长度方向在 Y 轴，所以 SLOT_L 和 SLOT_W 对调
                v_slot = Part.makeBox(SLOT_W + CUT_COMM, SLOT_L + CUT_COMM, T*2)
                v_slot.translate(App.Vector(sx - SLOT_W/2, sy - SLOT_L/2, -T/2))
                panel = panel.cut(v_slot)

    # 4. 处理按键孔 (只有 middle 和 cover 需要按键孔)
    if mode in ["middle", "cover"]:
        for bp in main_btns:
            btn_h = Part.makeCylinder(MAIN_D/2 + CUT_COMM, t*2)
            btn_h.translate(App.Vector(bp[0], bp[1], -t/2))
            panel = panel.cut(btn_h)
        for fp in func_btns:
            # 修正：功能键孔
            func_h = Part.makeCylinder(FUNC_D/2 + CUT_COMM, t*2)
            func_h.translate(App.Vector(fp[0], fp[1], -t/2))
            panel = panel.cut(func_h)
            
    panel = panel.removeSplitter()
    # 5. 生成对象
    obj = doc.addObject("Part::Feature", f"Panel_{mode}")
    obj.Shape = panel
    obj.Placement = App.Placement(App.Vector(0, 0, z_pos), App.Rotation())
    
    # 视觉区分
    if mode == "cover":
        obj.ViewObject.ShapeColor = (0.8, 0.9, 1.0)
        obj.ViewObject.Transparency = 30
    elif mode == "middle":
        obj.ViewObject.Transparency = 50
        
    return obj

# --- 5.1 函数：创建横向支撑板 ---
def create_support(y_pos):
    # 螺丝孔避让距离：螺丝孔在 12mm 处，我们从 25mm 开始到 L-25mm 结束
    margin_x = 23.0 

    # 支撑板主体尺寸
    s_length = L  - 2 * margin_x  # 比总长稍短，避免干涉圆角
    s_height = SUPPORT_H
    
    # 1. 创建主体（默认在 XY 平面，厚度为 T）
    # 我们先在本地坐标系画：X=长度, Y=高度, Z=厚度
    support = Part.makeBox(s_length, s_height, T)
    
    # 将主体移动到居中位置，方便后续旋转和定位
    support.translate(App.Vector(margin_x, 0, 0))
    
    # 2. 创建并合并榫头 (Tenons)
    # 这里的 sx 是面板上槽的 X 中心点
    for sx in support_x_positions:
        # 下榫头 (插入底板)
        tenon_bottom = Part.makeBox(SLOT_L, T, T)
        tenon_bottom.translate(App.Vector(sx - SLOT_L/2, -T, 0))
        support = support.fuse(tenon_bottom)
        
        # 上榫头 (插入顶板)
        tenon_top = Part.makeBox(SLOT_L, T, T)
        tenon_top.translate(App.Vector(sx - SLOT_L/2, s_height, 0))
        support = support.fuse(tenon_top)

    # 上面的支撑需要开USB和开关
    if y_pos >= W / 2:
        v_usb = Part.makeBox(12.2 + CUT_COMM, 5.5 + CUT_COMM, T*2)
        v_usb.translate(App.Vector(s_length *0.4, s_height/3, -T/2))
        support = support.cut(v_usb)

        v_power = Part.makeCylinder(FUNC_D/2 + CUT_COMM, T*2)
        v_power.translate(App.Vector(s_length *0.8, s_height/3, -T/2))
        support = support.cut(v_power)
    
    support = support.removeSplitter()

    # 3. 旋转和定位
    obj = doc.addObject("Part::Feature", f"Support_Y_{int(y_pos)}")
    obj.Shape = support
    
    # 默认是躺着的，需要绕 X 轴旋转 90 度竖起来
    # 然后移动到指定的 y_pos。注意 Z 轴起始高度应该是 T (避开底板)
    # 调整厚度居中：在 Y 轴方向减去 T/2
    obj.Placement = App.Placement(
        App.Vector(0, y_pos + T/2, T), 
        App.Rotation(App.Vector(1, 0, 0), 90)
    )
    return obj

# --- 5.2 函数：创建纵向支撑板 ---
def create_side_support(x_pos):
    # 纵向板长度：避开横向支撑板的厚度
    # 横向板在 y=12 和 y=88，所以纵向板长度设为 60mm 左右
    s_length_y = W - 40.0 
    s_height = SUPPORT_H
    
    # 1. 创建主体 (在 XY 平面，长边沿 Y 轴)
    # 注意：这里为了方便，先做 X=T, Y=长度, Z=高度 的 Box
    side_support = Part.makeBox(T, s_length_y, s_height)
    side_support.translate(App.Vector(0, (W - s_length_y)/2, 0))
    
    # 2. 添加榫头 (沿 Y 轴分布)
    for sy in side_support_y_slots:
        # 下榫头
        t_bottom = Part.makeBox(T, SLOT_L, T)
        t_bottom.translate(App.Vector(0, sy - SLOT_L/2, -T))
        side_support = side_support.fuse(t_bottom)
        
        # 上榫头
        t_top = Part.makeBox(T, SLOT_L, T)
        t_top.translate(App.Vector(0, sy - SLOT_L/2, s_height))
        side_support = side_support.fuse(t_top)
    
    side_support = side_support.removeSplitter()
    
    obj = doc.addObject("Part::Feature", f"Support_X_{int(x_pos)}")
    obj.Shape = side_support
    
    # 3. 定位
    # 因为创建时已经是垂直的(Z方向是高度)，所以只需移动到 x_pos
    # 稍微修正 X 偏移量使板材厚度居中
    obj.Placement = App.Placement(App.Vector(x_pos - T/2, 0, T), App.Rotation())
    
    return obj

# --- 6. 执行生成 ---
# 层级：
# Z=0: 底板 (带槽)
# Z=T to H-2T: 支撑柱 (此处由支撑板函数处理)
# Z=H-2T: 中层板 (带槽，固定按键)
# Z=H-T: 顶层覆盖板 (不带槽，沉头孔)

p_bottom = create_main_panel(0, mode="bottom")
p_middle = create_main_panel(H - T_COVER - T, mode="middle")
p_cover  = create_main_panel(H - T_COVER, mode="cover")

# 横向支撑 (前、后)
s_y1 = create_support(support_y_positions[0])
s_y2 = create_support(support_y_positions[1])

# 纵向支撑 (左、右)
s_x1 = create_side_support(side_support_x[0])
s_x2 = create_side_support(side_support_x[1])

# 设置透明度看内部铜柱结构
p_bottom.ViewObject.Transparency = 50
p_middle.ViewObject.Transparency = 50
p_cover.ViewObject.Transparency = 50

s_y1.ViewObject.Transparency = 50
s_y2.ViewObject.Transparency = 50
s_x1.ViewObject.Transparency = 50
s_x2.ViewObject.Transparency = 50

doc.recompute()

if EXPORT_DXF_ENABLE:
    if not os.path.exists(EXPORT_DXF_FOLDER):
        os.makedirs(EXPORT_DXF_FOLDER)
    
    parts_to_export = [
        {"name": "p_bottom", "obj": p_bottom, "dir": App.Vector(0,0,1)},
        {"name": "p_middle", "obj": p_middle, "dir": App.Vector(0,0,1)},
        {"name": "p_cover", "obj": p_cover, "dir": App.Vector(0,0,1)},
        {"name": "s_y1", "obj": s_y1, "dir": App.Vector(0,1,0)},
        {"name": "s_y2", "obj": s_y2, "dir": App.Vector(0,1,0)},
        {"name": "s_x1", "obj": s_x1, "dir": App.Vector(1,0,0)},
        {"name": "s_x2", "obj": s_x2, "dir": App.Vector(1,0,0)},
    ]
    
    for part in parts_to_export:
        # 构造完整文件路径
        name = part["name"]
        obj = part["obj"]
        dir = part["dir"]
        file_full_path = os.path.join(EXPORT_DXF_FOLDER, f"{name}.dxf")
        
        projection = Draft.make_shape2dview(obj,dir)
        
        App.ActiveDocument.recompute()
        doc.recompute()

        projection.Label = f"2D_{name}"
        # 执行导出：Draft.export 接收对象列表和文件名
        # 注意：DWG 导出通常需要对象被选中或作为列表传入
        importDXF.export([projection], file_full_path)
        App.ActiveDocument.removeObject(projection.Name)
        print(f"已导出: {file_full_path}")

doc.recompute()
