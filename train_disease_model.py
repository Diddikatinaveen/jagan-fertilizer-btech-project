"""Train and evaluate a MobileNetV2 leaf image classifier.

The supplied dataset must be licensed for this use and pre-split by plant/field
into train/<class>, validation/<class>, and test/<class> directories.
"""
import argparse
import hashlib
import json
from pathlib import Path

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}
IMAGE_SIZE = (224, 224)
MODEL_INPUT_METADATA = {
    "height": 224,
    "width": 224,
    "channels": 3,
    "preprocessing": "rescale_minus1_to1_in_model",
}


def image_files(directory):
    return sorted(
        path for path in directory.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    )


def class_directories(directory):
    return sorted(path.name for path in directory.iterdir() if path.is_dir())


def reject_cross_split_duplicates(split_directories):
    hashes = {}
    for split_name, directory in split_directories.items():
        for path in image_files(directory):
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            previous = hashes.get(digest)
            if previous:
                raise SystemExit(
                    f"Exact duplicate image appears in both {previous} and {split_name}; "
                    "remove the duplicate and re-check plant/field-level split leakage."
                )
            hashes[digest] = split_name


def read_class_mapping(mapping_path, class_names):
    try:
        supplied = json.loads(mapping_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SystemExit(f"Could not read class mapping JSON: {error}") from None
    if not isinstance(supplied, dict) or set(supplied) != set(class_names):
        raise SystemExit("Class mapping keys must exactly match all dataset class folder names.")

    classes = []
    for name in class_names:
        item = supplied[name]
        if not isinstance(item, dict):
            raise SystemExit(f"Class mapping for {name!r} must be a JSON object.")
        values = {
            "crop": item.get("crop"),
            "health": item.get("health"),
            "label_en": item.get("label_en"),
            "label_te": item.get("label_te"),
        }
        if (
            any(not isinstance(value, str) or not value.strip() for value in values.values())
            or values["health"] not in {"healthy", "diseased"}
        ):
            raise SystemExit(
                f"Class {name!r} needs non-empty crop, label_en, label_te, "
                "and health equal to healthy or diseased."
            )
        classes.append({"label": name, **{key: value.strip() for key, value in values.items()}})
    if not any(item["health"] == "healthy" for item in classes):
        raise SystemExit("Include at least one explicitly mapped healthy class.")
    return classes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True, help="Root containing train/, validation/, and test/ class folders")
    parser.add_argument("--class-map", required=True, help="JSON file mapping class folder names to crop/health/English/Telugu labels")
    parser.add_argument("--output", default="models/plant_disease.keras", help="Output Keras model path")
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--dataset-source", required=True, help="Dataset source URL or bibliographic reference")
    parser.add_argument("--dataset-license", required=True, help="Exact dataset license and permitted use")
    parser.add_argument("--dataset-limitations", required=True, help="Known collection, label, and field-domain limitations")
    args = parser.parse_args()
    if args.epochs < 1 or args.epochs > 100:
        raise SystemExit("--epochs must be between 1 and 100.")

    try:
        import tensorflow as tf
    except ImportError:
        raise SystemExit(
            "TensorFlow is optional. Install it in the training environment with "
            "`python -m pip install \"tensorflow>=2.15,<3.0\"`."
        ) from None

    root = Path(args.data)
    split_directories = {
        "train": root / "train",
        "validation": root / "validation",
        "test": root / "test",
    }
    if not all(directory.is_dir() for directory in split_directories.values()):
        raise SystemExit("Expected train/<class>, validation/<class>, and test/<class> directories.")
    classes = class_directories(split_directories["train"])
    if len(classes) < 2:
        raise SystemExit("At least two labelled classes are required.")
    for split_name, directory in split_directories.items():
        if class_directories(directory) != classes:
            raise SystemExit(f"The {split_name} split must contain the same class directories as train.")
        for class_name in classes:
            if not image_files(directory / class_name):
                raise SystemExit(f"No supported JPG/PNG images found for {class_name!r} in {split_name}.")
    reject_cross_split_duplicates(split_directories)
    class_labels = read_class_mapping(Path(args.class_map), classes)

    for split_name in ("validation", "test"):
        for class_name in classes:
            count = len(image_files(split_directories[split_name] / class_name))
            if count < 2:
                raise SystemExit(
                    f"At least two images per class are required in {split_name} for meaningful evaluation."
                )

    batch_size = 32
    train_ds = tf.keras.utils.image_dataset_from_directory(
        split_directories["train"],
        image_size=IMAGE_SIZE,
        batch_size=batch_size,
        label_mode="int",
        class_names=classes,
        shuffle=True,
        seed=42,
    )
    validation_ds = tf.keras.utils.image_dataset_from_directory(
        split_directories["validation"],
        image_size=IMAGE_SIZE,
        batch_size=batch_size,
        label_mode="int",
        class_names=classes,
        shuffle=False,
    )
    test_ds = tf.keras.utils.image_dataset_from_directory(
        split_directories["test"],
        image_size=IMAGE_SIZE,
        batch_size=batch_size,
        label_mode="int",
        class_names=classes,
        shuffle=False,
    )
    if train_ds.class_names != classes or validation_ds.class_names != classes or test_ds.class_names != classes:
        raise SystemExit("Dataset class ordering mismatch; refusing to save a mismapped model.")

    data_augmentation = tf.keras.Sequential([
        tf.keras.layers.RandomFlip("horizontal"),
        tf.keras.layers.RandomRotation(0.08),
        tf.keras.layers.RandomZoom(0.08),
    ], name="leaf_augmentation")
    base = tf.keras.applications.MobileNetV2(
        input_shape=(224, 224, 3),
        include_top=False,
        weights="imagenet",
    )
    base.trainable = False
    inputs = tf.keras.Input(shape=(224, 224, 3), name="rgb_0_255")
    x = tf.keras.layers.Rescaling(1.0 / 127.5, offset=-1, name="mobilenetv2_preprocess")(inputs)
    x = data_augmentation(x)
    x = base(x, training=False)
    x = tf.keras.layers.GlobalAveragePooling2D()(x)
    x = tf.keras.layers.Dropout(0.2)(x)
    outputs = tf.keras.layers.Dense(len(classes), activation="softmax", name="class_probabilities")(x)
    model = tf.keras.Model(inputs, outputs)
    model.compile(
        optimizer=tf.keras.optimizers.Adam(),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    model.fit(train_ds, validation_data=validation_ds, epochs=args.epochs)
    test_loss, test_accuracy = model.evaluate(test_ds, return_dict=False)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path = output_path.with_suffix(".metadata.json")
    model.save(output_path)
    metadata = {
        "schema_version": 1,
        "model_input": MODEL_INPUT_METADATA,
        "output": "softmax_class_probabilities",
        "confidence_threshold": 0.65,
        "classes": class_labels,
        "dataset": {
            "source": args.dataset_source,
            "license": args.dataset_license,
            "limitations": args.dataset_limitations,
            "split_policy": "Plant/field-grouped train, validation, and held-out test sets; exact duplicate file hashes checked.",
        },
        "evaluation": {
            "test_loss": float(test_loss),
            "test_accuracy": float(test_accuracy),
            "test_images": len(image_files(split_directories["test"])),
        },
        "training": {
            "architecture": "MobileNetV2 transfer learning",
            "tensorflow_version": tf.__version__,
            "input_size": list(IMAGE_SIZE),
            "seed": 42,
        },
    }
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Saved model:", output_path)
    print("Saved model metadata and class mapping:", metadata_path)
    print(f"Held-out test accuracy: {test_accuracy:.4f} (not a guarantee of field performance)")
    print("Supported crop/classes:", json.dumps(class_labels, ensure_ascii=False))


if __name__ == "__main__":
    main()
