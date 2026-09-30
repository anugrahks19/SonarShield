from ultralytics import YOLO

def resume_model_v6():
    # Load the last checkpoint
    model = YOLO(r"E:\GITHUB\a sih 2026\models\v6\detector_v6_p2_sss\weights\last.pt")

    # Resume training exactly where it left off
    model.train(resume=True)

if __name__ == "__main__":
    resume_model_v6()
