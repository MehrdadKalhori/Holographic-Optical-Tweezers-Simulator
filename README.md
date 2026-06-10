این متن کامل و نهایی `README.md` شماست که شامل تمام بخش‌های علمی، فرمول‌ها و توضیحات مهندسی است. آن را دقیقاً کپی کنید و در فایل `README.md` گیت‌هاب قرار دهید.

```markdown
# Holographic Optical Tweezers Studio 🔬

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![CustomTkinter](https://img.shields.io/badge/GUI-CustomTkinter-brightgreen)

An advanced physical simulation framework for Holographic Optical Tweezers (HOT) and Photothermal Langevin Dynamics. This software serves as a robust research and educational tool for biophotonics, bridging theoretical optical trapping models with real-time numerical simulations.

## 📸 Simulation Previews

**1. 3D Potential Well & Interference Force Field**
![Topology](assets/topology_shot.png)

**2. Brownian Motion Validation (Boltzmann PDF)**
![Validation](assets/validation_shot.png)

**3. Thermal Limits & Cavitation Warning**
![Cavitation](assets/cavitation_shot.png)

**4. Adaptive Optics (SLM Phase Mask)**
![SLM](assets/slm_shot.png)

## ✨ Key Scientific Features

* **Modular Software Architecture:** Separates core bio-optical numerical calculations from the visualization layer.
* **Rigorous Physics Engine:** * Computes 3D gradient forces using the Clausius-Mossotti polarizability:
      $$\alpha = 4 \pi \epsilon_m a^3 \frac{m^2 - 1}{m^2 + 2}$$
    * Models intensity distribution for Gaussian and Vortex (OAM) beams.
* **Tissue Turbidity Modeling:** Simulates photon attenuation in deep biological tissues using the Beer-Lambert law:
  $$I(z) = I_0 \exp(-\mu_s \cdot z)$$
* **Real-Time Langevin Dynamics:** Implements Monte Carlo simulations for Brownian motion under Stokes' Law ($F_{drag} = 6\pi\eta rv$), accounting for local photothermal heating and fluid viscosity fluctuations.
* **Adaptive Optics (SLM):** Simulates wavefront distortion corrections using Zernike polynomials (Spherical, Astigmatism, Coma) with Gerchberg-Saxton phase retrieval.
* **Statistical Validation:** Features a live telemetry dashboard that overlays numerical displacement data with the theoretical Boltzmann probability density function:
  $$P(x) \propto \exp\left(-\frac{U(x)}{k_B T}\right)$$

## 🚀 Repository Structure & Usage

* `physics_engine.py`: Contains core thermodynamic and optical formulas.
* `gui_main.py`: Manages the CustomTkinter UI framework and real-time Matplotlib rendering.
* `main.py`: The main entry point to execute the application.

### Installation
Clone the repository and install the required dependencies:
```bash
git clone [https://github.com/YourUsername/Holographic-Optical-Tweezers-Simulator.git](https://github.com/YourUsername/Holographic-Optical-Tweezers-Simulator.git)
cd Holographic-Optical-Tweezers-Simulator
pip install -r requirements.txt
python main.py

```

## 👥 Acknowledgements

Developed by **Mehrdad Kalhori** (Shahid Beheshti University) as an advanced biophotonics simulation portfolio.
Special thanks to my research teammates, **Sattar Jalali** and **Radman Moradi**, for their valuable discussions and collaborative insights during the conceptualization of the physics engine parameters.

---

*For academic inquiries or PhD opportunities, please connect with me via [LinkedIn](https://www.google.com/search?q=Your-LinkedIn-URL).*

```

```
