# EMX Batch Flow

The batch flow assumes the existing VM:

- Host: `192.168.37.128`
- User: `IC`
- EMX: `/home/IC/EDA/INTEGRAND60/bin/emx`
- Process: `/home/IC/EDA/INTEGRAND60/virtuoso_ui/emxinterface/processes/fdl_stack.proc`
- Cadence library: `codex_fdl_bridge`

Each candidate runs this sequence:

1. Generate FDL on Windows.
2. Convert FDL geometry into a Cadence SKILL layout builder.
3. Upload FDL/SKILL to the VM.
4. Run Virtuoso in batch to create `codex_fdl_bridge/<candidate>/layout`.
5. Run `strmout` to create GDS.
6. Run EMX with `Pdiff=P1:P2`.
7. Download `.s2p` and `.gds` back into `runs/v1`.

The EMX options are intentionally the same as the validated single-inductor run:

```text
--3d=m4,m5
--via-sidewalls=v4
--via-inductance=v4
--sweep 3e9 4.5e9
--sweep-stepsize=5e8
--internal=P1,m5,8
--internal=P2,m5,8
-p Pdiff=P1:P2
```

