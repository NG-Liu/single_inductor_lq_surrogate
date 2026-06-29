# Differential L/Q Definition

The project supports two Touchstone result styles.

For EMX differential 1-port output, EMX is run with:

```text
-p Pdiff=P1:P2
```

The resulting one-port `S11` is converted directly:

```text
Zdiff = Z0 * (1 + S11) / (1 - S11)
```

For UltraEM or generic two-port output, the full two-port Z matrix is used:

```text
Zdiff = Z11 + Z22 - Z12 - Z21
```

At the main frequency, do not interpolate L or Q directly. Interpolate complex `Zdiff` first:

```text
Zdiff(3.75GHz) = 0.5 * Zdiff(3.5GHz) + 0.5 * Zdiff(4.0GHz)
L = imag(Zdiff) / (2*pi*f)
Q = abs(imag(Zdiff) / real(Zdiff))
```

This convention was validated against the known `ind4b`/`l_test` inductor case: EMX and UltraEM differ by about `0.068%` in `L@3.75GHz`.

