#! /usr/bin/bash

# Build Script for the_lion_throne
pyinstaller Main.spec
rm -rI ../the_lion_throne
mv dist/the_lion_throne ../the_lion_throne
cp ../lex-talionis-utilities/audio_dlls/* ../the_lion_throne/