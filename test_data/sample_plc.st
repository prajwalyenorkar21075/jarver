PROGRAM Main
VAR
    StartBtn : BOOL;
    StopBtn : BOOL;
    EStopOK : BOOL;
    ConveyorRun : BOOL;
    StartDelay : TON;
    PartCount : CTU;
    i : INT;
END_VAR

IF StartBtn THEN
    ConveyorRun := TRUE;
END_IF;

IF StopBtn THEN
    ConveyorRun := FALSE;
END_IF;

EStopOK := TRUE;
ConveyorRun := TRUE;

FOR i := 1 TO 10 DO
    PartCount(CU := TRUE, PV := 5);
END_FOR;

RETURN;
StartDelay(IN := ConveyorRun, PT := T#2S);
END_PROGRAM
