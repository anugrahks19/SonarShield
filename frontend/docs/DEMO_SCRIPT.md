# SONAR-SHIELD demonstration script (about 3–5 minutes)

**Opening.** “SONAR-SHIELD helps a reviewer inspect side-scan sonar images and keep the machine assessment separate from the human assessment. Here is the current analysis workspace.”

**Upload and analysis.** Upload the Contact 105 test image. Point out the preview and the backend health state. Run analysis. Explain that the image goes to the F8 `/analyze` API, which calls the frozen detector, evidence, fusion, and decision pipeline. Wait for the completed response and show the candidate count.

**Inspect a candidate.** Select a candidate row and its sonar box. Zoom and pan briefly. Read the class, AI decision, fusion and evidence values exactly as displayed. If a field is unavailable, say so. Contact 105 has two spatially distinct candidates in the F9 smoke report, one GLOBAL and one TILED.

**Review and location.** Save a human assessment and note. Show that the AI decision remains unchanged. Open the map/localization section: the current examples are pixel-only, so no GPS target marker is shown. Geographic markers appear only when F8 supplies valid coordinates.

**Report and closing.** Open the report, show that both candidates and the human note are present, then export JSON or CSV. Explain that this is a review and reporting workflow around backend results. “The local integration works; deployment and the final backend freeze audit remain open release checks.”

If the API fails during the presentation, announce the switch to **DEMO MODE** and load a clearly labeled packaged example. Do not imply it is live inference. Avoid numerical accuracy, real-time, or geographic coverage claims unless supported by an independently documented measurement.
