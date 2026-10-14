# abstract spec
task is to bimplement a copilot skill dtah can be used to analyse images.
the images show street scenes, some with a pedestrian traffic light.
for the images with pedestrian taffic light the bounding boxes of the traffic lights are needed. the bounding boxes have coordinates based on as width 1000 and height 1000 scale per picture.
it the traiifi light shows red or green this state also has to be recogized. per imahe one json file with bounding box hat to be writtem containing also the state / color of the traffic light as red, green or unknown.
the positions of lights of cars or other signs shall not be recorded.
the skill will be give a directory as paramter. it will list all images and corresponding json files. the skill shall use a python script for that. the skill also receives a number of images to process. it will use the python script to determein that number of images that don't have a json yet. for these images the bounding boxes and traffic light states shall be written to json files.

first create ap implementation plan and write it to plan.md and clarify all open questions interactively 

