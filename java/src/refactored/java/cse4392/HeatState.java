package cse4392;

class HeatState implements SeasonState {

    @Override
    public void cool(SeasonSwitch context) {
        context.heater.off();
        context.ac.on();
        context.timer.start();
        SeasonSwitch.state = SeasonSwitch.COOL;
        System.out.println("Cooling started. RmTemp=" + context.room.temp);
    }

    @Override
    public void heat(SeasonSwitch context) {
        // Already heating; no operation required.
    }

    @Override
    public void off(SeasonSwitch context) {
        context.heater.off();
        context.timer.stop();
        SeasonSwitch.state = SeasonSwitch.OFF;
        System.out.println("Heating stopped. RmTemp=" + context.room.temp);
    }

    @Override
    public void timerOff(SeasonSwitch context) {
        if (context.room.temp < context.heatTemp) {
            context.heater.on();
            System.out.println("Heating started. RmTemp=" + context.room.temp);
        } else {
            context.heater.off();
            System.out.println("Heating stopped. RmTemp=" + context.room.temp);
        }
    }

    @Override
    public void roomActionPerformed(SeasonSwitch context) {
        if (context.heater.isOn) {
            context.room.temp++;
        } else {
            context.room.temp--;
        }
    }
}