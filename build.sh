# Build Script for the_lion_throne
# In Data/config.ini, turn cheat to 0
# In Data/config.ini, turn Screen Size to 3 and temp_ScreenSize to 3
# Make sure your old copy of the lion throne is backed up somewhere
pyinstaller main.spec
rm -rf ../the_lion_throne
mkdir ../the_lion_throne
mkdir ../the_lion_throne/the_lion_throne
mv dist/the_lion_throne ../the_lion_throne
cp ../lex-talionis-utilities/audio_dlls/* ../the_lion_throne/the_lion_throne
cp double_click_to_play.bat ../the_lion_throne
echo Done