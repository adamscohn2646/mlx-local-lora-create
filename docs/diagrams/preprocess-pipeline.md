# Preprocess pipeline diagram

How `preprocess` works for the Lilien LoRA project. **Green** = built · **Yellow** = planned · **Gray** = optional/off.

See also: [lora-preprocessing PRD](../stories/lora-preprocessing/PRD.md), [lora_preprocessing_spec.md](../../lora_preprocessing_spec.md).

---

## Big picture

Everything is driven by one config file. Stages run in order; each reads the previous stage's output and writes new artifacts under `work_dir`. **Source images are never modified.**

```mermaid
flowchart TB
    subgraph config["config/lilien.yaml"]
        SRC["paths.source_dir<br/>(your Lilien folder)"]
        WORK["paths.work_dir<br/>work/lilien/"]
        OUT["paths.output_dir<br/>output/lilien/"]
        RULES["quality_rules<br/>min 512px, aspect ≤ 2.0"]
        CAP["captioning.*<br/>(Slice 3+)"]
    end

    subgraph source["READ ONLY — never written"]
        RAW["102 raw files<br/>jpg/png/jpeg/svg/tif"]
    end

    subgraph stage1["Stage 1: inventory ✓ BUILT"]
        INV["Scan + classify each file"]
        INVJSON["inventory.json"]
        INVMD["inventory_report.md"]
    end

    subgraph stage2["Stage 2: normalize ✓ BUILT"]
        NORM["Copy GOOD files → JPG RGB"]
        NORMDIR["normalized/<br/>49 images"]
        NORMLOG["normalization_log.json"]
    end

    subgraph stage3["Stage 3: caption ✓ BUILT"]
        VLM["Qwen3-VL-4B per image"]
        CAPJSON["captions/*.json<br/>(Part A, B, C)"]
        CAPTXT["captions/*.txt<br/>(Part C for training)"]
        QA["caption_qa.md"]
    end

    subgraph stage4["Stage 4: rerender — optional, OFF"]
        I2I["mflux img2img<br/>img2img.enabled: false"]
        RER["rerendered/"]
    end

    subgraph stage5["Stage 5: assemble ✓ BUILT"]
        ASM["Match images + captions"]
        MAN["manifest.jsonl"]
        FINAL["output/lilien/<br/>images/ + captions/"]
    end

    SRC --> RAW
    RAW --> INV
    RULES --> INV
    INV --> INVJSON
    INV --> INVMD

    INVJSON --> NORM
    RAW --> NORM
    NORM --> NORMDIR
    NORM --> NORMLOG

    NORMDIR --> VLM
    CAP --> VLM
    VLM --> CAPJSON
    VLM --> CAPTXT
    CAPTXT --> QA

    NORMDIR --> I2I
    CAPJSON --> I2I
    I2I -.-> RER

    NORMDIR --> ASM
    RER -.-> ASM
    CAPTXT --> ASM
    ASM --> MAN
    ASM --> FINAL
    OUT --> FINAL

    style stage1 fill:#d4edda
    style stage2 fill:#d4edda
    style stage3 fill:#d4edda
    style stage4 fill:#e9ecef
    style stage5 fill:#d4edda
    style source fill:#f8f9fa
```

---

## CLI entry points

```mermaid
flowchart LR
    CLI["python -m preprocess"]

    CLI --> INV_CMD["inventory<br/>--config config/lilien.yaml"]
    CLI --> NORM_CMD["normalize<br/>--config config/lilien.yaml"]
    CLI --> CAP_CMD["caption<br/>--limit 10 --resume"]
    CLI --> ASM_CMD["assemble"]
    CLI --> ALL["all<br/>--skip-rerender"]

    INV_CMD --> S1["Stage 1"]
    NORM_CMD --> S2["Stage 2"]
    CAP_CMD --> S3["Stage 3"]
    ASM_CMD --> S5["Stage 5"]
    ALL --> S1
    ALL --> S2

    style S1 fill:#d4edda
    style S2 fill:#d4edda
    style S3 fill:#d4edda
    style S5 fill:#d4edda
```

---

## Stage 1: Inventory

Read-only scan. No copies, no edits.

```mermaid
flowchart TD
    F["Each file in source_dir"]

    F --> E1{Extension?}
    E1 -->|.tif .tiff .svg| SKIP["SKIPPED<br/>(7 files)"]
    E1 -->|.jpg .jpeg .png| OPEN["Open with Pillow<br/>read width, height, color mode"]
    E1 -->|other| UNK["UNKNOWN"]

    OPEN -->|cannot open| ERR["ERROR"]
    OPEN --> OK["Compute short_side,<br/>aspect_ratio"]

    OK --> R1{short_side<br/>&lt; 512?}
    R1 -->|yes| DROP1["DROP<br/>(24 files)"]
    R1 -->|no| R2{aspect<br/>&gt; 2.0?}
    R2 -->|yes| DROP2["DROP"]
    R2 -->|no| R3{short_side<br/>&lt; 1024?}
    R3 -->|yes| BORD["BORDERLINE<br/>(22 files)"]
    R3 -->|no| GOOD["GOOD<br/>(49 files)"]

    GOOD --> OUT1["inventory.json"]
    BORD --> OUT1
    DROP1 --> OUT1
    DROP2 --> OUT1
    ERR --> OUT1
    SKIP --> OUT1
    OUT1 --> OUT2["inventory_report.md<br/>(human review)"]
```

---

## Stage 2: Normalize

Only `GOOD` files from inventory (unless `--include-borderline`).

```mermaid
flowchart TD
    INV["inventory.json<br/>filter status = GOOD"]
    SRC["Original in source_dir<br/>(read only)"]

    INV --> LOOP["For each GOOD file"]
    SRC --> LOOP

    LOOP --> COPY["Copy to work/lilien/normalized/"]
    COPY --> RGB{"Color mode<br/>RGB?"}
    RGB -->|no| CONV["Convert → RGB"]
    RGB -->|yes| FMT
    CONV --> FMT{"Already JPG?"}
    FMT -->|no| JPG["Re-encode as JPG q=95"]
    FMT -->|yes| DONE["Keep dimensions<br/>(no resize)"]

    JPG --> DONE
    DONE --> LOG["normalization_log.json"]

    LOOP -->|one file fails| CONT["Log error, continue"]
```

---

## Directories (Lilien project)

```mermaid
flowchart LR
    subgraph external["Outside repo"]
        DATA["DataSets/EphraimMosheLillian/<br/>102 originals — untouched"]
    end

    subgraph repo["Repo"]
        CFG["config/lilien.yaml"]
        subgraph work["work/lilien/"]
            IJ["inventory.json"]
            IR["inventory_report.md"]
            ND["normalized/ (49 JPG)"]
            NL["normalization_log.json"]
            CJ["captions/*.json + *.txt"]
            CQA["caption_qa.md"]
        end
        subgraph output["output/lilien/ ✓"]
            OI["images/ (49)"]
            OC["captions/ (49)"]
            MF["manifest.jsonl"]
        end
    end

    CFG --> work
    DATA --> IJ
    DATA --> ND
    ND --> CJ
    CJ --> output
```

---

## Stage 3: Caption (sequence)

```mermaid
sequenceDiagram
    participant You
    participant CLI as preprocess caption
    participant Norm as normalized/
    participant VLM as Qwen3-VL-4B
    participant Cap as captions/
    participant QA as caption_qa.md

    You->>CLI: --config lilien.yaml --limit 10
    CLI->>Norm: list JPG files (sorted)
    loop each image (up to limit)
        CLI->>VLM: image + 3-part prompt template
        VLM-->>CLI: Part A, B, C text
        CLI->>Cap: {stem}.json (full response)
        CLI->>Cap: {stem}.txt (Part C only)
    end
    CLI->>QA: flag bad trigger phrases,<br/>word counts, banned words
    You->>Cap: review captions before full run
```

Part **C** → training caption (trigger phrase + description). Part **B** → img2img rerender only (disabled for Lilien).

---

## Revision log

| Date | Change |
|------|--------|
| 2026-05-25 | Slice 4 assemble built; Lilien v3 49 pairs → `output/lilien/` |
| 2026-05-25 | Slice 3 caption stage built; VLM resize cache noted |
