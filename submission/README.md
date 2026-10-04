# Judge demo downloads

- [Editable judge deck](m212_20261004/SONAR_SHIELD_Judge_Deck.pptx)
- [Static demo ZIP without model weights](m212_20261004/SONAR_SHIELD_Demo.zip)
- [Judge instructions](../docs/JUDGE_WALKTHROUGH.md)

Download and extract the ZIP. Open a terminal in its `frontend-static` directory and run:

```powershell
python -m http.server 8783 --bind 127.0.0.1
```

Open http://127.0.0.1:8783/ and explicitly choose a verified example. Static hosting has no live gateway or cloud routes. The four paired examples, review UI and report downloads are interactive. Live inference and cloud records use https://sonarshield26.vercel.app/analysis.

The full local archive includes experimental weights and is not committed. This public archive includes no secrets, survey datasets or model weights. New M2.08 weights are not deployed and 80/80 remains unmet. [Release evidence](../docs/MODULE2_M211_RELEASE.md).
