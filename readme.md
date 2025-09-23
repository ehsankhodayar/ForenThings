# ForenThings: An Interactive Framework for Crime Scene Reconstruction in IoT Forensics

> **TL;DR**: ForenThings is an interactive framework for IoT forensics that reconstructs crime scenes from device and app events without requiring source code access. It turns IoT devices and apps into responsive agents, enabling collaborative investigation, and achieves full data provenance coverage with negligible runtime and resource overhead in both normal and attack scenarios.

<!-- Replace the shield placeholders below when public -->

<p align="left">
  <a href="https://github.com/ehsankhodayar/ForenThings/blob/master/LICENSE"><img alt="License" src="https://img.shields.io/badge/License-MIT-informational"></a>
  <a href="https://www.python.org/downloads/"><img alt="Python" src="https://img.shields.io/badge/Python-3.10%2B-blue"></a>
  <a href="https://github.com/ehsankhodayar/ForenThings"><img alt="Status" src="https://img.shields.io/badge/status-📦_public_release-brightgreen"></a>
  <a href="#citation"><img alt="DOI" src="https://img.shields.io/badge/DOI-TBD-orange"></a>
  <a href="https://dl.acm.org/journal/tiot"><img alt="Venue" src="https://img.shields.io/badge/ACM%20TIOT-Accepted-9cf"></a>
</p>

---

## Overview

ForenThings is a **practical, platform-centric IoT forensic framework** that addresses the lack of effective crime scene reconstruction tools for modern IoT environments. Unlike traditional solutions that rely on static code analysis or instrumentation—which are often infeasible due to restricted access to smart app source code—ForenThings leverages the logs of devices and smart apps as published by IoT platforms. It then transforms each IoT device and app into a **responsive agent** capable of answering forensic queries about its past activities. By correlating these logs, ForenThings reconstructs crime scenes as provenance graphs, allowing investigators to analyze causes, consequences, and dependencies of incidents.

We developed a prototype of ForenThings on the **SmartThings platform**, and evaluated it using realistic smart home automation scenarios, including both normal usage and 12 classes of real-world IoT attack scenarios. The results show that ForenThings achieves **100% coverage of relevant forensic data sources** with minimal runtime and resource overhead.

> Ehsan Khodayarseresht, Sofya Smolyakova, Lianying Zhao, Armin Mansouri, Suryadipta Majumdar, and Mauro Conti. *ForenThings: An Interactive Framework for Crime Scene Reconstruction in IoT Forensics*. ACM Transactions on Internet of Things (TIOT), 2025.

## Key Contributions

* We design a practical IoT forensic approach, ForenThings, that performs crime scene reconstruction in smart homes without code instrumentation. To our knowledge, ForenThings is the first IoT forensic approach that can accurately identify dependencies between different data sources without utilizing code instrumentation or static code analysis.
* We introduce an agent conversation approach that creates an abstraction layer for IoT devices and smart apps and allows them to respond to queries about their past activities, which can potentially be leveraged for other security purposes beyond forensics (e.g., auditing).
* We implement a ForenThings prototype based on the SmartThings platform. We also plan to make the prototype source code and its dataset available upon publication.
* We evaluate the effectiveness and efficiency of ForenThings with simulated and real IoT devices and sensors and 12 different classes of actual smart home attacks. Furthermore, we evaluate our methodology against state-of-the-art approaches, including ProvThings [62], SmartTracer [42], and IoTFlow [53]. The provenance coverage measurement and performance metrics illustrate that ForenThings can detect 100% of all essential related data sources to a given incident with minimal overhead.

## Repository Layout

```
ForenThings/
├─ bots/                 # device-app agents codes
├─ database/             # local DB schema (no private data)
├─ example/              # how to use ForenThings?
├─ forenlog/             # core parsing module for processing raw collected logs
├─ frontend/             # UI for interactive analysis
├─ .gitignore            # ignored git files
├─ requirements.txt      # installed python packages and their versions
├─ LICENSE               # the ForenThings license
├─ main.py               # entry point (CLI launcher)
└─ README.md
```

## Quick Start

### Requirements

* Python **3.10+** (tested on 3.10)
* OS: Linux/macOS/Windows
* Graphviz (for graph rendering)

### Install

```bash
# 1) Create a virtual environment
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 2) Install packages & extras
pip install -U pip wheel
pip install -r requirements.txt  # or: pip install .[all]
```

### Datasets

To experiment with ForenThings, download the prepared datasets from [Google Drive](https://drive.google.com/file/d/1TdQ_uO7O1dRwIJl6A_QXQwmzVgUb6Nqm/view?usp=sharing). After downloading, unzip the archive into your desired folder:

```bash
unzip ForenThings_datasets.zip -d forenthings_datasets/
```

## Using ForenThings

### CLI

1. **Execute** `main.py`:

   ```bash
   python main.py
   ```

2. **Load a dataset** into the ForenThings database:

   * Choose option `[1] Log Manager` → `[1] Log Files Processing`.
   * Enter the dataset directory path (e.g., `...\ForenThings\datasets\malicious Device Handler\Dataset`).
   * The system will process the log files and import them into the database.
   * If you see a warning like `An Unsupported file is detected: 042_s.txt`, answer **yes** to `Do you want to ignore this file? (y/n):` and continue.
   * If you previously imported the same dataset, first clear it using `[2] Delete Records of Tables` to avoid conflicts.

3. **Start a forensic investigation**:

   * Return to the main menu → choose `[2] Forensics Investigation`.
   * Select investigation type:

     * **Global Investigation**: reconstructs the crime scene for all events (options include *ForenFull*, *ForenBack*, *ForenBackComplete*, *ForenForward*).
     * **Device Investigation**: focuses on a specific IoT device within a chosen time window.
     * **Location Investigation**: focuses on a specific location within the environment.

4. **Save results**:

   * After selecting the investigation type, provide a destination path where the system will store the reconstruction results.

### Example

🎥 [Watch the demo video](example/ForenThings_Example.mp4)

## Evaluation

To access our evaluation results, please use the link below:

[Evaluation Results](https://drive.google.com/file/d/1s-8dnqTQ-gK_3YDpMw83GHyAk_gOcVsU/view?usp=sharing)

## Citation

Please cite the paper if you use ForenThings: TBD

[//]: # (**ACM Reference &#40;placeholder&#41;:**)

[//]: # ()
[//]: # (> *Author1*, *Author2*, and *Author3*. 2025. **ForenThings: An Interactive Framework for Crime Scene Reconstruction in IoT Forensics**. *ACM Transactions on Internet of Things &#40;TIOT&#41;*. [https://doi.org/XXXX]&#40;https://doi.org/XXXX&#41;)

[//]: # ()
[//]: # (**BibTeX &#40;placeholder&#41;:**)

[//]: # ()
[//]: # (```bibtex)

[//]: # (@article{forenthings2025,)

[//]: # (  title   = {ForenThings: An Interactive Framework for Crime Scene Reconstruction in IoT Forensics},)

[//]: # (  author  = {Your Name and Coauthor, Another},)

[//]: # (  journal = {ACM Transactions on Internet of Things},)

[//]: # (  year    = {2025},)

[//]: # (  volume  = {TBD},)

[//]: # (  number  = {TBD},)

[//]: # (  pages   = {TBD},)

[//]: # (  doi     = {10.1145/TBD})

[//]: # (})

[//]: # (```)

[//]: # (Replace placeholders once the TIOT citation is finalized.)

## License

This project is licensed under the **MIT License** – a permissive open-source license commonly used for academic and research code. You are free to use, modify, and distribute the software, provided that the original copyright notice and license terms are included in any copies or substantial portions of the software.

See the [LICENSE](LICENSE) file for the full text.

## Acknowledgments

[//]: # (This work was supported by *\[funders/grants]* and built on *\[dependencies/tools]*.)
TBD

