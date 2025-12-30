#include <CH55xSwitchControl.h>

#define ButtonNum 12
#define HATCOUNT  4

#define UP 0
#define DOWN 1
#define LEFT 2
#define RIGHT 3

const uint8_t Pins[ButtonNum] = {
  32, 14, 15, 16,    //up down left right
  10, 11, 31, 30,    //A B X Y
  17, 35, 34, 33     //LB RB - +
};

const uint16_t KeyCode[ButtonNum] = {
  0, 0, 0, 0,
  BUTTON_A, BUTTON_B, BUTTON_X, BUTTON_Y,
  BUTTON_L, BUTTON_R, BUTTON_MINUS, BUTTON_PLUS
};

bool BUTTON_STATUS[ButtonNum] = {
  false, false, false, false,
  false, false, false, false,
  false, false, false, false
};
bool BUTTON_STATUS_P[ButtonNum] = {
  false, false, false, false,
  false, false, false, false,
  false, false, false, false
};

uint8_t DPAD_DIR = HAT_CENTER;
uint8_t DPAD_DIR_LAST = HAT_CENTER;

bool shouldSendReport = false;

void setup() {
  for (int i = 0; i < ButtonNum; i++) {
    pinMode(Pins[i], INPUT_PULLUP);
  }
  setAutoSendReport(false);
  USBInit();
}

void loop() {
  for (byte i = 0; i < ButtonNum; i++) {
    BUTTON_STATUS[i] = !digitalRead(Pins[i]);
  }
  DPAD_DIR = HAT_CENTER;

  if (BUTTON_STATUS[UP]) {
    DPAD_DIR = HAT_UP;
  } else if (BUTTON_STATUS[DOWN]) {
    DPAD_DIR = HAT_DOWN;
  } else if (BUTTON_STATUS[LEFT]) {
    DPAD_DIR = HAT_LEFT;
  } else if (BUTTON_STATUS[RIGHT]) {
    DPAD_DIR = HAT_RIGHT;
  }

  if (BUTTON_STATUS[UP] && BUTTON_STATUS[RIGHT]) {
    DPAD_DIR = HAT_RIGHT_UP;
  } else if (BUTTON_STATUS[UP] && BUTTON_STATUS[LEFT]) {
    DPAD_DIR = HAT_UP_LEFT;
  } else if (BUTTON_STATUS[DOWN] && BUTTON_STATUS[RIGHT]) {
    DPAD_DIR = HAT_RIGHT_DOWN;
  } else if (BUTTON_STATUS[DOWN] && BUTTON_STATUS[LEFT]) {
    DPAD_DIR = HAT_DOWN_LEFT;
  }

  if (DPAD_DIR != DPAD_DIR_LAST) {
    pressHatButton(DPAD_DIR);
    shouldSendReport = true;
    DPAD_DIR_LAST = DPAD_DIR;
  }

  for (int i = HATCOUNT; i < ButtonNum; i++) {
    if (BUTTON_STATUS_P[i] != BUTTON_STATUS[i]) {
      shouldSendReport = true;
      BUTTON_STATUS_P[i] = BUTTON_STATUS[i];
      if (BUTTON_STATUS[i]) {
        pressButton(KeyCode[i]);
      } else {
        releaseButton(KeyCode[i]);
      }
    }
  }

  if (shouldSendReport)
  {
    sendReport();
    shouldSendReport = false;
  }
  delay(5);  //naive debouncing
}
