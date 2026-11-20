package cse4392;

interface SeasonState {
    void cool(SeasonSwitch context);

    void heat(SeasonSwitch context);

    void off(SeasonSwitch context);

    void timerOff(SeasonSwitch context);

    void roomActionPerformed(SeasonSwitch context);
}