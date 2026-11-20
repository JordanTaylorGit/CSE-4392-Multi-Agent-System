package cse4392;

import static org.junit.jupiter.api.Assertions.*;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

/**
 * Hand-written safety-net tests for SeasonSwitch.
 * Organized as the (state x event) matrix: 3 states x 4 events, plus Room ticks.
 * The same tests should pass on the State-pattern refactor.
 */
class SeasonSwitchTest {

    SeasonSwitch s;

    @BeforeEach
    void setUp() {
        SeasonSwitch.state = SeasonSwitch.OFF; // state is static: reset every test
        s = new SeasonSwitch();
    }

    @AfterEach
    void tearDown() {
        s.timer.stop();           // never leave a real Swing timer running
        s.room.timer.stop();
        SeasonSwitch.state = SeasonSwitch.OFF;
    }

    // ---------- cool() ----------

    @Test
    void cool_fromOff_turnsAcOnAndGoesToCool() {
        s.cool();
        assertEquals(SeasonSwitch.COOL, SeasonSwitch.state);
        assertTrue(s.ac.isOn);
        assertFalse(s.heater.isOn);
    }

    @Test
    void cool_fromCool_doesNothing() {
        s.cool();
        s.ac.isOn = false; // if cool() did anything, this would flip back to true
        s.cool();
        assertEquals(SeasonSwitch.COOL, SeasonSwitch.state);
        assertFalse(s.ac.isOn);
    }

    @Test
    void cool_fromHeat_switchesHeaterOffAcOn() {
        s.heat();
        s.cool();
        assertEquals(SeasonSwitch.COOL, SeasonSwitch.state);
        assertTrue(s.ac.isOn);
        assertFalse(s.heater.isOn);
    }

    // ---------- heat() ----------

    @Test
    void heat_fromOff_turnsHeaterOnAndGoesToHeat() {
        s.heat();
        assertEquals(SeasonSwitch.HEAT, SeasonSwitch.state);
        assertTrue(s.heater.isOn);
        assertFalse(s.ac.isOn);
    }

    @Test
    void heat_fromHeat_doesNothing() {
        s.heat();
        s.heater.isOn = false;
        s.heat();
        assertEquals(SeasonSwitch.HEAT, SeasonSwitch.state);
        assertFalse(s.heater.isOn);
    }

    @Test
    void heat_fromCool_switchesAcOffHeaterOn() {
        s.cool();
        s.heat();
        assertEquals(SeasonSwitch.HEAT, SeasonSwitch.state);
        assertTrue(s.heater.isOn);
        assertFalse(s.ac.isOn);
    }

    // ---------- off() ----------

    @Test
    void off_fromOff_doesNothing() {
        s.off();
        assertEquals(SeasonSwitch.OFF, SeasonSwitch.state);
        assertFalse(s.ac.isOn);
        assertFalse(s.heater.isOn);
    }

    @Test
    void off_fromHeat_turnsHeaterOffAndGoesToOff() {
        s.heat();
        s.off();
        assertEquals(SeasonSwitch.OFF, SeasonSwitch.state);
        assertFalse(s.heater.isOn);
    }

    @Test
    void off_fromCool_turnsAcOffAndGoesToOff() {
        s.cool();
        s.off();
        assertEquals(SeasonSwitch.OFF, SeasonSwitch.state);
        assertFalse(s.ac.isOn);
    }

    // ---------- timerOff() ----------

    @Test
    void timerOff_inOff_doesNothing() {
        s.ac.isOn = true;
        s.heater.isOn = true;
        s.timerOff();
        assertEquals(SeasonSwitch.OFF, SeasonSwitch.state);
        assertTrue(s.ac.isOn);
        assertTrue(s.heater.isOn);
    }

    @Test
    void timerOff_inCool_tempAboveThreshold_acOn() {
        s.cool();
        s.ac.isOn = false;
        s.room.temp = s.coolTemp + 1; // 69: just above 68
        s.timerOff();
        assertTrue(s.ac.isOn);
    }

    @Test
    void timerOff_inCool_tempAtThreshold_acOff() {
        s.cool();
        s.room.temp = s.coolTemp; // 68: boundary, NOT greater than
        s.timerOff();
        assertFalse(s.ac.isOn);
    }

    @Test
    void timerOff_inHeat_tempBelowThreshold_heaterOn() {
        s.heat();
        s.heater.isOn = false;
        s.room.temp = s.heatTemp - 1; // 76: just below 77
        s.timerOff();
        assertTrue(s.heater.isOn);
    }

    @Test
    void timerOff_inHeat_tempAtThreshold_heaterOff() {
        s.heat();
        s.room.temp = s.heatTemp; // 77: boundary, NOT less than
        s.timerOff();
        assertFalse(s.heater.isOn);
    }

    // ---------- Room.actionPerformed (temperature tick) ----------

    @Test
    void roomTick_inOff_tempUnchanged() {
        s.room.temp = 70;
        s.room.actionPerformed(null);
        assertEquals(70, s.room.temp);
    }

    @Test
    void roomTick_inCool_acOn_tempDrops() {
        s.cool();
        s.room.temp = 70;
        s.room.actionPerformed(null);
        assertEquals(69, s.room.temp);
    }

    @Test
    void roomTick_inCool_acOff_tempRises() {
        s.cool();
        s.ac.isOn = false;
        s.room.temp = 70;
        s.room.actionPerformed(null);
        assertEquals(71, s.room.temp);
    }

    @Test
    void roomTick_inHeat_heaterOn_tempRises() {
        s.heat();
        s.room.temp = 70;
        s.room.actionPerformed(null);
        assertEquals(71, s.room.temp);
    }

    @Test
    void roomTick_inHeat_heaterOff_tempDrops() {
        s.heat();
        s.heater.isOn = false;
        s.room.temp = 70;
        s.room.actionPerformed(null);
        assertEquals(69, s.room.temp);
    }

    // ---------- Invalid state (implicit default branch of each switch) ----------

    @Test
    void invalidState_isIgnoredByEveryMethod() {
        SeasonSwitch.state = 3; // not OFF/COOL/HEAT
        s.room.temp = 70;
        assertDoesNotThrow(() -> {
            s.cool();
            s.heat();
            s.off();
            s.timerOff();
            s.room.actionPerformed(null);
        });
        assertEquals(3, SeasonSwitch.state);
        assertEquals(70, s.room.temp);
        assertFalse(s.ac.isOn);
        assertFalse(s.heater.isOn);
    }

    @Test
    void actionPerformed_delegatesToTimerOff() {
        s.cool();
        s.ac.isOn = false;
        s.room.temp = s.coolTemp + 1;   // above threshold, so timerOff turns AC on
        s.actionPerformed(null);
        assertTrue(s.ac.isOn);
    }
}
