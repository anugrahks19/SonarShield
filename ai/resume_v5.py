from ultralytics import YOLO

def resume_model_v5():
    # Load the last checkpoint
    model = YOLO(r"E:\GITHUB\a sih 2026\models\v5\detector_v5_m640\weights\last.pt")

    # Resume training exactly where it left off (restores epoch, optimizer, and scheduler)
    model.train(resume=True)

if __name__ == "__main__":
    resume_model_v5()
