package cse4392;

class OffState implements SeasonState {

    @Override
    public void cool(SeasonSwitch context) {
        context.ac.on();
        context.timer.start();
        SeasonSwitch.state = SeasonSwitch.COOL;
        System.out.println("Cooling started. RmTemp=" + context.room.temp);
    }

    @Override
    public void heat(SeasonSwitch context) {
        context.heater.on();
        context.timer.start();
        SeasonSwitch.state = SeasonSwitch.HEAT;
        System.out.println("Heating started. RmTemp=" + context.room.temp);
    }

    @Override
    public void off(SeasonSwitch context) {
        // Already off; no operation required.
    }

    @Override
    public void timerOff(SeasonSwitch context) {
        // No temperature regulation while off.
    }

    @Override
    public void roomActionPerformed(SeasonSwitch context) {
        // Room temperature does not drift while off.
    }
}