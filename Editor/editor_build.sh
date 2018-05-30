#! /usr/bin/bash

# Build Script for the LevelEditor
pyinstaller LevelEditor.spec
rm -rf ../../LevelEditor
mv dist/Editor ../../LevelEditor
echo Done