"""
Configure Android build configuration for mobile application.
Aligns Android Gradle Plugin to 8.6.0, Gradle to 8.7, and compileSdk to 36
for compatibility with modern camera and scanner plugins (mobile_scanner 6.0+).
"""

import os
import re
import sys

def configure_android(mobile_dir: str):
    android_dir = os.path.join(mobile_dir, "android")
    if not os.path.exists(android_dir):
        print(f"Android directory not found at {android_dir}")
        return False

    # 1. Update settings.gradle with AGP 8.6.0 and Kotlin 2.0.0
    settings_gradle = os.path.join(android_dir, "settings.gradle")
    if os.path.exists(settings_gradle):
        with open(settings_gradle, "r", encoding="utf-8") as f:
            content = f.read()
        content = re.sub(
            r'id\s+"com\.android\.application"\s+version\s+"[^"]+"',
            'id "com.android.application" version "8.6.0"',
            content,
        )
        content = re.sub(
            r'id\s+"org\.jetbrains\.kotlin\.android"\s+version\s+"[^"]+"',
            'id "org.jetbrains.kotlin.android" version "2.0.0"',
            content,
        )
        with open(settings_gradle, "w", encoding="utf-8") as f:
            f.write(content)
        print("Updated settings.gradle to AGP 8.6.0 and Kotlin 2.0.0")

    # 2. Update gradle-wrapper.properties to Gradle 8.7
    wrapper_props = os.path.join(android_dir, "gradle", "wrapper", "gradle-wrapper.properties")
    if os.path.exists(wrapper_props):
        with open(wrapper_props, "r", encoding="utf-8") as f:
            content = f.read()
        content = re.sub(r'gradle-[\d.]+-all\.zip', 'gradle-8.7-all.zip', content)
        with open(wrapper_props, "w", encoding="utf-8") as f:
            f.write(content)
        print("Updated gradle-wrapper.properties to Gradle 8.7")

    # 3. Update app/build.gradle with compileSdk 36, minSdk 23, ndkVersion 26.1.10909125 and Java 17
    app_build_gradle = os.path.join(android_dir, "app", "build.gradle")
    if os.path.exists(app_build_gradle):
        with open(app_build_gradle, "r", encoding="utf-8") as f:
            content = f.read()
        content = re.sub(r'compileSdk\s*=\s*flutter\.compileSdkVersion', 'compileSdk = 36', content)
        content = re.sub(r'minSdk\s*=\s*flutter\.minSdkVersion', 'minSdk = 23', content)
        content = re.sub(r'ndkVersion\s*=\s*flutter\.ndkVersion', 'ndkVersion = "26.1.10909125"', content)
        content = content.replace("JavaVersion.VERSION_1_8", "JavaVersion.VERSION_17")
        content = content.replace('"1.8"', '"17"')
        with open(app_build_gradle, "w", encoding="utf-8") as f:
            f.write(content)
        print("Updated app/build.gradle to compileSdk 36, minSdk 23, ndkVersion 26.1.10909125 and Java 17")

    return True

if __name__ == "__main__":
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    mobile_dir = os.path.join(base_dir, "mobile")
    if len(sys.argv) > 1:
        mobile_dir = os.path.abspath(sys.argv[1])
    success = configure_android(mobile_dir)
    sys.exit(0 if success else 1)
