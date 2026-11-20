package cse4392;

class CoolState implements SeasonState {

    @Override
    public void cool(SeasonSwitch context) {
        // Already cooling; no operation required.
    }

    @Override
    public void heat(SeasonSwitch context) {
        context.ac.off();
        context.heater.on();
        context.timer.start();
        SeasonSwitch.state = SeasonSwitch.HEAT;
        System.out.println("Heating started. RmTemp=" + context.room.temp);
    }

    @Override
    public void off(SeasonSwitch context) {
        context.ac.off();
        context.timer.stop();
        SeasonSwitch.state = SeasonSwitch.OFF;
        System.out.println("Cooling stopped. RmTemp=" + context.room.temp);
    }

    @Override
    public void timerOff(SeasonSwitch context) {
        if (context.room.temp > context.coolTemp) {
            context.ac.on();
            System.out.println("Cooling started. RmTemp=" + context.room.temp);
        } else {
            context.ac.off();
            System.out.println("Cooling stopped. RmTemp=" + context.room.temp);
        }
    }

    @Override
    public void roomActionPerformed(SeasonSwitch context) {
        if (context.ac.isOn) {
            context.room.temp--;
        } else {
            context.room.temp++;
        }
    }
}