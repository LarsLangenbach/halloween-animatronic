# M1 layout fit table

Margins in mm: + = inside the allowed envelope, - = sticking out; the part named is the worst one.
Envelopes: eyes and lids inside the outer skin; lip plates inside the skin's inner surface;
jaw and frame inside the skull's inner surface. Eye <-> mouth: closest approach, - = overlap.

| scale | head W x L x H | eye <-> mouth closest | eyemech eyes | eyemech lids | eyemech frame | mouth lips | mouth surfaces | mouth jaw | mouth frame |
|---|---|---|---|---|---|---|---|---|---|
| 1.00 | 156 x 210 x 297 | -17.3 (SnapEyemech_v20 / TopBase overlap 5161 mm3) | -3.5 (Component74, 2 out) | -6.4 (LidTR, 4 out) | -16.1 (Base, 11 out) | +1.7 (UpperLeftLip) | +9.3 (Part_1) | -10.7 (Part_33, 2 out) | -3.5 (M3_Shoulder, 16 out) |
| 1.10 | 172 x 231 x 327 | -4.3 (SnapEyemech_v20 / TopBase overlap 80 mm3) | +0.2 (Component74) | -2.4 (LidTR, 4 out) | -11.6 (Base, 7 out) | +1.8 (UpperLeftLip) | +9.2 (Part_1) | -3.1 (Part_33, 2 out) | -0.9 (M3_Shoulder, 2 out) |
| 1.20 | 187 x 252 x 356 | +2.5 (Base / TopBase) | +3.8 (Component74) | +1.6 (LidTR) | -7.2 (Base, 5 out) | +1.9 (UpperLeftLip) | +9.1 (Part_1) | +3.6 (Part_33) | +1.6 (Part_29) |
| 1.30 | 203 x 273 x 386 | +9.3 (Base / TopBase) | +7.3 (Component74) | +5.4 (LidTR) | -2.9 (Base, 2 out) | +1.9 (UpperLeftLip) | +9.1 (Part_1) | +9.1 (Part_33) | +3.0 (Part_29) |

## Parts outside their envelope at scale 1.0

- eyemech frame `Base`: -16.1 mm outside skull_inner
- eyemech frame `Base`: -16.1 mm outside skull_inner
- eyemech frame `SnapEyemech_v20`: -15.2 mm outside skull_inner
- eyemech frame `2xBottomLidLever`: -10.8 mm outside skull_inner
- eyemech frame `2xBottomLidLever`: -10.8 mm outside skull_inner
- mouth jaw `Part_33`: -10.7 mm outside skull_inner
- mouth jaw `JawLink`: -10.4 mm outside skull_inner
- eyemech frame `PivotLarge`: -7.8 mm outside skull_inner
- eyemech frame `PivotLarge`: -7.7 mm outside skull_inner
- eyemech lids `LidTR`: -6.4 mm outside head_outer
- eyemech lids `LidTR`: -6.4 mm outside head_outer
- eyemech lids `LidBR`: -5.5 mm outside head_outer
- eyemech lids `LidBR`: -5.4 mm outside head_outer
- mouth frame `M3_Shoulder`: -3.5 mm outside skull_inner
- eyemech eyes `Component74`: -3.5 mm outside head_outer

Renders: layout.png (and layout_1..6.png)
