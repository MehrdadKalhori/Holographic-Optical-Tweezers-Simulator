"""
Crafted by Mehrdad Y. Kalhori, straight out of the Wild West of Lorestan, Iran 🤠
Main Entry Point for Holographic Optical Tweezers Studio
Run this file to launch the application.
"""

# ایمپورت کردن کلاس رابط کاربری از فایل دوم
from gui_main import AdvancedTweezersApp

if __name__ == "__main__":
    # ساخت یک نمونه از برنامه و اجرای حلقه اصلی
    app = AdvancedTweezersApp()
    app.mainloop()