export ANDROIDAPI="26"
p4a apk --private . --package=com.greentwip.lextalionis --name "Lex Talionis" --version 0.1 --bootstrap=sdl2 --requirements=python3,pygame,kivy --sdk-dir ~/Android/Sdk --ndk-dir ~/Android/ndk/r19c --orientation sensorLandscape
