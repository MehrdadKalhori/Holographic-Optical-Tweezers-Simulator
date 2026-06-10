"""
Crafted by Mehrdad Y. Kalhori, straight out of the Wild West of Lorestan, Iran 🤠
Physics Engine for Holographic Optical Tweezers Simulation
Handles core numerical modeling of gradient forces, intensity profiles, and scattering.
"""

import numpy as np

class OpticalTweezersSimulation:
    def __init__(self, wavelength, laser_power, beam_waist, n_medium, n_particle, r_particle, mode="Gaussian", mu_s=0.0):
        self.wavelength = wavelength
        self.P = laser_power
        self.w0 = beam_waist  
        self.nm = n_medium
        self.np = n_particle
        self.a = r_particle
        self.mode = mode
        self.mu_s = mu_s 
        
        # Physical Constants
        self.c = 3e8
        self.epsilon0 = 8.854e-12
        self.epsilon_m = (self.nm ** 2) * self.epsilon0
        self.lambda_m = self.wavelength / self.nm
        self.zR = (np.pi * (self.w0 ** 2)) / self.lambda_m
        self.I0 = (2 * self.P) / (np.pi * (self.w0 ** 2))
        
        # Clausius-Mossotti polarizability
        m = self.np / self.nm
        self.alpha = 4 * np.pi * self.epsilon_m * (self.a ** 3) * ((m**2 - 1)/(m**2 + 2))

    def calculate_intensity(self, x, y, z):
        """
        Calculates the 3D intensity profile of the laser beam.
        Incorporates Beer-Lambert law for tissue scattering (mu_s) and supports OAM profiles.
        """
        r_sq = x**2 + y**2
        w_z = self.w0 * np.sqrt(1 + (z / self.zR) ** 2)
        
        # Tissue Turbidity Attenuation
        attenuation = np.exp(-self.mu_s * np.abs(z)) if self.mu_s > 0 else 1.0
        
        # Gaussian Profile
        I_gauss = self.I0 * (self.w0 / w_z)**2 * np.exp(-2 * r_sq / (w_z**2)) * attenuation
        
        # Laguerre-Gaussian (Vortex/OAM) Profile Modulator
        if self.mode == "Vortex (OAM)":
            return I_gauss * (2 * r_sq / (w_z**2)), w_z
            
        return I_gauss, w_z