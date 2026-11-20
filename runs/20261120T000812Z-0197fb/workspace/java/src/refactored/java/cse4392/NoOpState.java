package cse4392;

class NoOpState implements SeasonState {

    @Override
    public void cool(SeasonSwitch context) {
        // Unrecognized state; no operation required.
    }

    @Override
    public void heat(SeasonSwitch context) {
        // Unrecognized state; no operation required.
    }

    @Override
    public void off(SeasonSwitch context) {
        // Unrecognized state; no operation required.
    }

    @Override
    public void timerOff(SeasonSwitch context) {
        // Unrecognized state; no operation required.
    }

    @Override
    public void roomActionPerformed(SeasonSwitch context) {
        // Unrecognized state; no operation required.
    }
}