import torch, torchvision
print("Torch Version:", torch.__version__)
print("CUDA available:", torch.cuda.is_available())
# import detectron2 logger
import detectron2
# from detectron2.utils.logger import setup_logger
# setup_logger()

# import detectron2 utilities
from detectron2 import model_zoo
from detectron2.engine import DefaultPredictor
from detectron2.config import get_cfg
from detectron2.data import MetadataCatalog, DatasetCatalog

# import common libraries
import os, json, random
import cv2
import numpy as np
import requests
from requests.exceptions import HTTPError, Timeout


def main():

    imageURL1 = "https://storage.googleapis.com/segmentation-testing/testing_images1/bikes.jpeg"
    imageURL2 = "https://storage.googleapis.com/segmentation-testing/testing_images1/beach.jpeg"
    imageURL3 = "https://storage.googleapis.com/segmentation-testing/testing_images1/buildings.JPG"
    # create model
    model = SegmentationModel()
    predictor = model.builtModel(UsingCPU=True) #set to False when using a GPU
    # make list of images to run
    image_preprocessing = ImagePreProcessing()
    image_preprocessing.loadImage(imageURL1)
    image_preprocessing.loadImage(imageURL2)
    image_preprocessing.loadImage(imageURL3)
    imageList = image_preprocessing.getImages()
    # perform prediction for every image
    for imageData in imageList:
        imageURL, image = imageData
        prediction = model.getPrediction(predictor, image)
        print("Image URL:", imageURL)
        # print(">>> Instance segmentation classes prediction:\n", prediction["instances"].pred_classes)
        # print(">>> Instance segmentation mask prediction:\n", prediction["instances"].pred_masks)
        # print(">>> Panoptic segmentation mask prediction:\n", prediction["panoptic_seg"][1])
        labels_things, labels_stuff = model.getLabels_PanopticSeg(prediction)
        print(">>>Panoptic Seg (things) labels:", labels_things)
        print(">>>Panoptic Seg (stuff) labels:", labels_stuff)
        masks, mask_labels = model.getMasks_InstanceSeg(prediction, labels=True)
        print(">>>Instance Seg (things) mask labels:", mask_labels)
        for i in range(0, len(masks)):
            print("Label:", mask_labels[i])
            print(masks[i])


class SegmentationModel():
    
    def __init__(self):
        self.url = str()
        self.thing_classes = list()
        self.stuff_classes = list()

    def builtModel(self, UsingCPU=True):
        # create configuration
        cfg = get_cfg()
        # add config 
        cfg.merge_from_file(model_zoo.get_config_file("COCO-PanopticSegmentation/panoptic_fpn_R_101_3x.yaml"))
        # set threshold for this model; means that inference has to be greater than 50%
        cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.5  
        # Find model weights
        cfg.MODEL.WEIGHTS = model_zoo.get_checkpoint_url("COCO-PanopticSegmentation/panoptic_fpn_R_101_3x.yaml")
        if (UsingCPU == True):
            # ***Add line below only if inference will be made on a CPU:
            cfg.MODEL.DEVICE='cpu'
        #run an inference against the predictor:
        predictor = DefaultPredictor(cfg)
        # store model classes 
        self.thing_classes = MetadataCatalog.get(cfg.DATASETS.TRAIN[0]).thing_classes
        self.stuff_classes = MetadataCatalog.get(cfg.DATASETS.TRAIN[0]).thing_classes
        return predictor

    def getPrediction(self, predictor, image):
        outputs = predictor(image)
        return outputs

    def getLabels_PanopticSeg(self, modelPrediction):
        # Get class ID (category_id) and the class it belongs to (thing_class or stuff_class)
        # ---> modelPrediction must be a Dictionary type output by panoptic seg model
        classID = list()
        panoptic_seg, segments_info = modelPrediction["panoptic_seg"]
        # get category for every object found my model
        for i in range(len(segments_info)):
            classID.append([segments_info[i]['category_id'], segments_info[i]['isthing']])
        # get the labels
        labels_things= list()
        labels_stuff = list()
        for i in range(len(classID)):
            # if true, object belongs to thing_class
            if classID[i][1] == True:
                labels_things.append(self.thing_classes[classID[i][0]])
            else:
                labels_stuff.append(self.stuff_classes[classID[i][0]])
        return (labels_things, labels_stuff)

    def getMasks_InstanceSeg(self, modelPrediction, labels=False):
        pass
        # convert instance predictions to numpy arrays
        maskClassIDs = modelPrediction["instances"].pred_classes.numpy()
        masks =modelPrediction["instances"].pred_masks.numpy()
        # return labels if labels argument set to True
        if (labels == True):
            maskLabels = list()
            for i in range(len(maskClassIDs)):
                # print(thing_classes[maskClassID[i]])
                maskLabels.append(self.thing_classes[maskClassIDs[i]])
            return (masks, maskLabels)
        return masks


class ImagePreProcessing():
    def __init__(self):
        self.images = list()

    def getImages(self):
        return self.images

    def loadImage(self, imageUrl):
        self.url = imageUrl
        # Use requests to issue a standard HTTP GET 
        try:
            image_response = requests.get(imageUrl ,timeout=15)
            # raise_for_status will throw an exception if an HTTP error
            image_response.raise_for_status
            print(image_response)
            # get image as numpy array
            image_NumpyArray = np.frombuffer(image_response.content, np.uint8)
            image = cv2.imdecode(image_NumpyArray, cv2.IMREAD_COLOR)
            # append to images to be run on model
            self.images.append([imageUrl, image])

        except HTTPError as err:
            print("Error: {0}".format(err))
        except Timeout as err:
            print("Request time out {0}".format(err))


if __name__ == "__main__":
    main()