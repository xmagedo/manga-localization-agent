from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api import manga_routes, review_routes
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Routers
app.include_router(manga_routes.router)
app.include_router(review_routes.router)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
def healthz():
    return {"status": "ok"}







# import os
# import tkinter as tk
# from tkinter import filedialog, Canvas, Scrollbar, Text, Button
# from PIL import Image, ImageTk
# from manga_ocr import MangaOcr
# import json
# from roboflow import Roboflow
# import csv
# import requests
# import openai
# import torch 
# from ultralytics import YOLO 
# import numpy as np


# mocr = MangaOcr()

# def load_model(model_path):
#     # Instantiate the model for prediction only
#     model = YOLO(model_path, task='predict')
#     return model

# def load_model_panel(model_path_panel):
#     model_panel = YOLO(model_path_panel, task='predict')
#     return model_panel

# model_path = '/Users/abdulmajeedalroumi/Documents/Manga_detection_files/best.pt'
# model_path_panel = '/Users/abdulmajeedalroumi/Documents/Manga_detection_files/best_panel_detection.pt'
# model = load_model(model_path)

# model_panel = load_model_panel(model_path_panel)

# # Function to extract Japanese text using OCR
# def extract_japanese_text(image):
#     try:
#         text = mocr(image)
#         print(f"Extracted text: {text}")
#         return text
#     except Exception as e:
#         print(f"An error occurred during OCR: {e}")
#         return ""

# class StartPage(tk.Tk):
#     def __init__(self):
#         super().__init__()
#         self.title("Manga OCR Tool")
#         self.geometry("300x200")
#         self.button = Button(self, text="Select Manga Image", command=self.select_image)
#         self.button.pack(pady=20)

#     def select_image(self):
#         image_path = filedialog.askopenfilename(
#             title="Select a Manga Image",
#             filetypes=[("PNG Files", "*.png"), ("JPEG Files", "*.jpg"), ("JPEG Files", "*.jpeg"), ("BMP Files", "*.bmp"), ("GIF Files", "*.gif"), ("All Files", "*.*")]
#         )
#         if image_path:
#             self.destroy()  # Close the start page
#             app = TextBubbleApp()
#             app.process_image(image_path)  # Call process_image on the app instance
#             app.mainloop()  # Start the main event loop of the application
#         else:
#             print("No image selected.")

# class TextBubbleApp(tk.Tk):
#     def __init__(self):
#         super().__init__()
#         self.model = load_model(model_path)  # Load the bubble detection model
#         self.model_panel = model_panel       # Directly assign the already loaded panel detection model
#         self.bubbles = []
#         self.panels = []
#         self.image = None
#         self.image_path = None
#         self.bubble_counter = 0
#         self.panel_counter = 0
#         self.japanese_text = ""
#         self.text_items = []
#         self.selected_item = None
#         self.selection_start = None
#         self.selection_end = None
#         self.selected_area = None
#         self.bubbles_data = []
#         self.processed_bubbles = set()
#         self.panel_bubble_counts = {}
#         self.protocol("WM_DELETE_WINDOW", self.on_closing)

    
#     def convert_to_native_types(self, d):
#         if isinstance(d, dict):
#             return {k: self.convert_to_native_types(v) for k, v in d.items()}
#         elif isinstance(d, list):
#             return [self.convert_to_native_types(v) for v in d]
#         elif isinstance(d, (torch.Tensor, np.ndarray)):
#             return d.tolist()
#         elif isinstance(d, (np.float32, np.float64)):
#             return float(d)
#         elif isinstance(d, (np.int32, np.int64)):
#             return int(d)
#         else:
#             return d


#     def process_image(self, image_path):
#         print(f"Processing image: {image_path}")
#         self.image_path = image_path
#         self.image = Image.open(image_path)
#         self.tk_image = ImageTk.PhotoImage(self.image)
#         self.display_width, self.display_height = self.image.size
#         self.original_width, self.original_height = self.image.size
#         self._create_widgets()
#         self.canvas.config(scrollregion=self.canvas.bbox("all"))

#         try:
#             # Detect bubbles
#             results = self.model(image_path)
#             print(f"Model results: {results}")  # Debug: Full results

#             if isinstance(results, list):
#                 results = results[0]

#             # Check if the results object has bounding boxes
#             if hasattr(results, 'boxes') and results.boxes is not None and len(results.boxes) > 0:
#                 self.bubbles = []
#                 for box in results.boxes.xyxy:
#                     x1, y1, x2, y2 = map(int, box[:4].cpu().numpy())
#                     scaled_bbox = {
#                         'x': x1,
#                         'y': y1,
#                         'width': x2 - x1,
#                         'height': y2 - y1
#                     }
#                     self.bubbles.append(scaled_bbox)
#                     print(f"Detected bubble: {scaled_bbox}")  # Debug: Detected bubble

#                     cropped_image = self.image.crop((x1, y1, x2, y2))
#                     japanese_text = extract_japanese_text(cropped_image)

#                     # Append bubble data to bubbles_data list
#                     self.bubbles_data.append({
#                         'bubble_no': self.bubble_counter,
#                         'panel_no': 0,  # Default panel number to 0 initially
#                         'japanese_text': japanese_text,
#                         'coordinates': {
#                             'x1': x1,
#                             'y1': y1,
#                             'x2': x2,
#                             'y2': y2
#                         }
#                     })
#                     self.bubble_counter += 1

#                     # Draw the rectangle for each bubble
#                     self.canvas.create_rectangle(
#                         x1, y1, x2, y2,
#                         outline="green", width=2
#                     )

#         #     # Detect panels
#         #     panel_results = self.model_panel(image_path)
#         #     print(f"Panel model results: {panel_results}")  # Debug: Full results

#         #     if isinstance(panel_results, list):
#         #         panel_results = panel_results[0]

#         #     # Check if the results object has bounding boxes for panels
#         #     if hasattr(panel_results, 'boxes') and panel_results.boxes is not None and len(panel_results.boxes) > 0:
#         #         self.panels = []
#         #         for box in panel_results.boxes.xyxy:
#         #             x1, y1, x2, y2 = map(int, box[:4].cpu().numpy())

#         #             # Ensure x1, y1, x2, y2 are valid before proceeding
#         #             if x1 is not None and y1 is not None and x2 is not None and y2 is not None:
#         #                 scaled_panel_bbox = {
#         #                     'x': x1,
#         #                     'y': y1,
#         #                     'width': x2 - x1,
#         #                     'height': y2 - y1,
#         #                     'panel_no': len(self.panels) + 1  # Assign panel number
#         #                 }
#         #                 self.panels.append(scaled_panel_bbox)
#         #                 print(f"Detected panel: {scaled_panel_bbox}")  # Debug: Detected panel

#         #                 # Update panel_no for bubbles within this panel
#         #                 for bubble in self.bubbles_data:
#         #                     if self.bubble_within_panel(bubble['coordinates'], scaled_panel_bbox):
#         #                         bubble['panel_no'] = scaled_panel_bbox['panel_no']

#         #                 # Draw the rectangle for each panel
#         #                 self.canvas.create_rectangle(
#         #                     x1, y1, x2, y2,
#         #                     outline="blue", width=2  # Use a different color for panels
#         #                 )
#         #             else:
#         #                 print("Invalid panel coordinates detected, skipping this panel.")

#         #     self.canvas.update()

#         # except Exception as e:
#         #     print(f"An error occurred: {e}")
#             # Detect panels
#             panel_results = self.model_panel(image_path)
#             print(f"Panel model results: {panel_results}")  # Debug: Full results

#             if isinstance(panel_results, list):
#                 panel_results = panel_results[0]

#             if hasattr(panel_results, 'boxes') and panel_results.boxes is not None and panel_results.boxes.xyxy.size(0) > 0:
#                 panel_bboxes = panel_results.boxes.xyxy.cpu().numpy()
#                 self.panels = []
#                 for panel_bbox in panel_bboxes:
#                     scaled_panel_bbox = {
#                         'x': int(panel_bbox[0]),
#                         'y': int(panel_bbox[1]),
#                         'width': int(panel_bbox[2] - panel_bbox[0]),
#                         'height': int(panel_bbox[3] - panel_bbox[1]),
#                         'panel_no': len(self.panels) + 1  # Assign panel number
#                     }
#                     self.panels.append(scaled_panel_bbox)
#                     print(f"Detected panel: {scaled_panel_bbox}")  # Debug: Detected panel

#                     self.canvas.create_rectangle(
#                         scaled_panel_bbox['x'], scaled_panel_bbox['y'],
#                         scaled_panel_bbox['x'] + scaled_panel_bbox['width'], scaled_panel_bbox['y'] + scaled_panel_bbox['height'],
#                         outline="blue", width=2  # Use a different color for panels
#                     )

#             self.canvas.update()

#         except Exception as e:
#             print(f"An error occurred: {e}")

#     def bubble_within_panel(self, bubble, panel):
#         # Extract bubble and panel coordinates
#         bubble_x1, bubble_y1 = bubble['x1'], bubble['y1']
#         bubble_x2, bubble_y2 = bubble['x2'], bubble['y2']
#         panel_x1, panel_y1 = panel['x'], panel['y']
#         panel_x2 = panel_x1 + panel['width']
#         panel_y2 = panel_y1 + panel['height']

#         # Check if the bubble is within the panel's bounding box
#         return (panel_x1 <= bubble_x1 <= panel_x2 and
#                 panel_y1 <= bubble_y1 <= panel_y2 and
#                 panel_x1 <= bubble_x2 <= panel_x2 and
#                 panel_y1 <= bubble_y2 <= panel_y2)



#     def _create_widgets(self):
#         main_frame = tk.Frame(self)
#         main_frame.pack(fill=tk.BOTH, expand=True)

#         # Frame for the image
#         image_frame = tk.Frame(main_frame)
#         image_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

#         # Frame for the text display
#         text_frame = tk.Frame(main_frame)
#         text_frame.pack(side=tk.RIGHT, fill=tk.Y)

#         # Add the canvas to the image frame
#         self.canvas = Canvas(image_frame, width=self.image.width, height=self.image.height, scrollregion=(0, 0, self.image.width, self.image.height))
#         self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
#         self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)

#         # Add the text display to the text frame
#         self.japanese_text_display = tk.Text(text_frame, height=10, width=50)
#         self.japanese_text_display.pack(side=tk.TOP, fill=tk.X)
#         self.japanese_text_display.insert(tk.END, self.japanese_text)

#         # Add scrollbars
#         self.v_scroll = Scrollbar(image_frame, orient="vertical", command=self.canvas.yview)
#         self.v_scroll.pack(side="right", fill="y")
#         self.h_scroll = Scrollbar(image_frame, orient="horizontal", command=self.canvas.xview)
#         self.h_scroll.pack(side="bottom", fill="x")

#         # Configure the canvas to use the scrollbars
#         self.canvas.configure(yscrollcommand=self.v_scroll.set, xscrollcommand=self.h_scroll.set)

#         # Bind events after creating the canvas
#         self._bind_events()

#     def convert_yolo_predictions_to_bboxes(self, results):
#         pixel_bounding_boxes = []
#         if hasattr(results, 'boxes') and results.boxes.xyxy.size > 0:
#             for bbox in results.boxes.xyxy:
#                 x1, y1, x2, y2, conf, cls = bbox
#                 print(f"BBox: x1={x1}, y1={y1}, x2={x2}, y2={y2}")  # Debug: Print bounding box coordinates
#                 pixel_bounding_boxes.append({
#                     'x': int(x1),
#                     'y': int(y1),
#                     'width': int(x2 - x1),
#                     'height': int(y2 - y1)
#                 })
#         return pixel_bounding_boxes

#     def _bind_events(self):
#         self.canvas.bind("<Button-1>", self.on_mouse_click)
#         self.canvas.bind("<B1-Motion>", self.on_drag)
#         self.canvas.bind("<ButtonRelease-1>", self.on_mouse_release)

#     def on_mouse_click(self, event):
#         self.selection_start = (self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))
#         canvas_x = self.canvas.canvasx(event.x)
#         canvas_y = self.canvas.canvasy(event.y)
#         clicked_bubble = self.identify_bubble(canvas_x, canvas_y)

#         if clicked_bubble:
#             clicked_bubble_id = (clicked_bubble["x"], clicked_bubble["y"], clicked_bubble["width"], clicked_bubble["height"])
#             if clicked_bubble_id not in self.processed_bubbles:
#                 self.perform_ocr_on_bubble(clicked_bubble)
#                 self.mark_bubble_as_processed(clicked_bubble_id)

#     def on_drag(self, event):
#         canvas_x = self.canvas.canvasx(event.x)
#         canvas_y = self.canvas.canvasy(event.y)
#         self.selection_end = (canvas_x, canvas_y)
#         self.canvas.delete(self.selected_area)  # Remove previous selection rectangle
#         self.selected_area = self.canvas.create_rectangle(
#             self.selection_start[0], self.selection_start[1],
#             self.selection_end[0], self.selection_end[1],
#             outline='red'
#         )

#     def perform_ocr_on_selection(self, x1, y1, x2, y2):
#         # Ensure coordinates are in the correct order
#         x1, x2 = sorted([x1, x2])
#         y1, y2 = sorted([y1, y2])

#         # Calculate the scaling factors
#         scale_x = self.original_width / self.display_width
#         scale_y = self.original_height / self.display_height

#         # Scale the coordinates
#         scaled_x1 = x1 * scale_x
#         scaled_y1 = y1 * scale_y
#         scaled_x2 = x2 * scale_x
#         scaled_y2 = y2 * scale_y

#         print(f"OCR Selection coordinates: ({scaled_x1}, {scaled_y1}) to ({scaled_x2}, {scaled_y2})")
#         print(f"Original dimensions: ({self.original_width}x{self.original_height})")
#         print(f"Displayed dimensions: ({self.display_width}x{self.display_height})")
#         print(f"Scaling factors: (scale_x={scale_x}, scale_y={scale_y})")
#         print("Attempting to identify bubble within selected area...")

#         # Check the entire selection area for overlap with any bubbles
#         selected_bubble = None
#         for bubble in self.bubbles:
#             bubble_x1 = bubble['x']
#             bubble_y1 = bubble['y']
#             bubble_x2 = bubble_x1 + bubble['width']
#             bubble_y2 = bubble_y1 + bubble['height']

#             print(f"Checking bubble: {bubble}")

#             # Check if the selection area overlaps with the bubble
#             if not (scaled_x2 < bubble_x1 or scaled_x1 > bubble_x2 or scaled_y2 < bubble_y1 or scaled_y1 > bubble_y2):
#                 selected_bubble = bubble
#                 break

#         if not selected_bubble:
#             print(f"No bubble identified in the selected area. Center coordinates: ({(scaled_x1 + scaled_x2) / 2}, {(scaled_y1 + scaled_y2) / 2})")
            
#             # If no bubble is identified, perform OCR on the selected area directly
#             cropped_image = self.image.crop((scaled_x1, scaled_y1, scaled_x2, scaled_y2))
#             japanese_text = extract_japanese_text(cropped_image)
#             print(f"Extracted text from selected area: {japanese_text}")

#             # Add the OCR result to the bubbles data
#             self.bubbles_data.append({
#                 'bubble_no': self.bubble_counter,
#                 'panel_no': 0,  # Assuming 0 if no panel information is available
#                 'japanese_text': japanese_text,
#                 'coordinates': {
#                     'x1': scaled_x1,
#                     'y1': scaled_y1,
#                     'x2': scaled_x2,
#                     'y2': scaled_y2
#                 }
#             })
#             self.bubble_counter += 1

#             print(f"Drawing red rectangle at: x1={scaled_x1}, y1={scaled_y1}, x2={scaled_x2}, y2={scaled_y2}")

#             # Draw a red rectangle around the selected area
#             self.canvas.create_rectangle(
#                 x1, y1, x2, y2,
#                 outline="red", width=2
#             )
#             self.canvas.update_idletasks()

#             print("Current bubbles data:")
#             print(json.dumps(self.convert_to_native_types(self.bubbles_data), ensure_ascii=False, indent=4))
#             return

#         print(f"Selected bubble: {selected_bubble}")

#         # Crop the image to the bubble's coordinates
#         cropped_image = self.image.crop((selected_bubble["x"], selected_bubble["y"], selected_bubble["x"] + selected_bubble["width"], selected_bubble["height"]))

#         # Perform OCR on the cropped image
#         japanese_text = extract_japanese_text(cropped_image)
#         print(f"Extracted text from selected bubble: {japanese_text}")

#         # Add the OCR result to the bubble data
#         panel_no = self.identify_panel_for_bubble(selected_bubble)

#         if panel_no not in self.panel_bubble_counts:
#             self.panel_bubble_counts[panel_no] = 0
#         self.panel_bubble_counts[panel_no] += 1

#         bubble_no = self.panel_bubble_counts[panel_no]

#         self.bubbles_data.append({
#             'bubble_no': bubble_no,
#             'panel_no': panel_no,
#             'japanese_text': japanese_text,
#             'coordinates': {
#                 'x1': selected_bubble["x"],
#                 'y1': selected_bubble["y"],
#                 'x2': selected_bubble["x"] + selected_bubble["width"],
#                 'y2': selected_bubble["y"] + selected_bubble["height"]
#             }
#         })
#         self.bubble_counter += 1

#         print(f"Drawing green rectangle at: x1={selected_bubble['x']}, y1={selected_bubble['y']}, x2={selected_bubble['x'] + selected_bubble['width']}, y2={selected_bubble['y'] + selected_bubble['height']}")

#         # Draw a green rectangle around the selected bubble
#         self.canvas.create_rectangle(
#             selected_bubble["x"], selected_bubble["y"],
#             selected_bubble["x"] + selected_bubble["width"], selected_bubble["y"] + selected_bubble["height"],
#             outline="green", width=2
#         )
#         self.canvas.update_idletasks()

#         print("Current bubbles data:")
#         print(json.dumps(self.convert_to_native_types(self.bubbles_data), ensure_ascii=False, indent=4))






#     def automatic_ocr_processing(self):
#         for bubble in self.bubbles:
#             if (bubble["x"], bubble["y"], bubble["width"], bubble["height"]) not in self.processed_bubbles:
#                 self.perform_ocr_on_bubble(bubble)
#                 self.mark_bubble_as_processed((bubble["x"], bubble["y"], bubble["width"], bubble["height"]))

#     # def perform_ocr_on_bubble(self, bubble):
#     #     cropped_image = self.image.crop((bubble["x"], bubble["y"], bubble["x"] + bubble["width"], bubble["height"]))
#     #     japanese_text = extract_japanese_text(cropped_image)
#     #     arabic_text = self.translate_text(japanese_text)

#     #     print(f"Drawing green rectangle at: x1={bubble['x']}, y1={bubble['y']}, x2={bubble['x'] + bubble['width']}, y2={bubble['y'] + bubble['height']}")  # Debug: Print drawing coordinates

#     #     self.canvas.create_rectangle(
#     #         bubble["x"], bubble["y"], 
#     #         bubble["x"] + bubble["width"], bubble["y"] + bubble["height"], 
#     #         outline="green", width=2
#     #     )
#     #     self.canvas.update_idletasks()  # Ensure the canvas updates

#     #     panel_no = self.identify_panel_for_bubble(bubble)
#     #     if panel_no not in self.panel_bubble_counts:
#     #         self.panel_bubble_counts[panel_no] = 0
#     #     self.panel_bubble_counts[panel_no] += 1

#     #     bubble_no = self.panel_bubble_counts[panel_no]

#     #     # Convert all values to native Python types
#     #     self.bubbles_data.append({
#     #         'bubble_no': int(bubble_no),
#     #         'panel_no': int(panel_no),
#     #         'japanese_text': japanese_text,
#     #         'arabic_text': arabic_text,
#     #         'coordinates': {
#     #             'x1': float(bubble["x"]),
#     #             'y1': float(bubble["y"]),
#     #             'x2': float(bubble["x"] + bubble["width"]),
#     #             'y2': float(bubble["y"] + bubble["height"])
#     #         }
#     #     })
#     #     self.bubble_counter += 1

#     def perform_ocr_on_bubble(self, bubble):
#         cropped_image = self.image.crop((bubble["x"], bubble["y"], bubble["x"] + bubble["width"], bubble["height"]))
#         print(f"Performing OCR on cropped image with size: {cropped_image.size}")  # Debug: Cropped image size

#         try:
#             japanese_text = extract_japanese_text(cropped_image)
#             print(f"Extracted text: {japanese_text}")  # Debug: Extracted text
#         except Exception as e:
#             print(f"An error occurred during OCR extraction: {e}")
#             japanese_text = ""

#         arabic_text = self.translate_text(japanese_text)
#         panel_no = self.identify_panel_for_bubble(bubble)
#         if panel_no not in self.panel_bubble_counts:
#             self.panel_bubble_counts[panel_no] = 0
#         self.panel_bubble_counts[panel_no] += 1

#         bubble_no = self.panel_bubble_counts[panel_no]

#         # Convert all values to native Python types
#         self.bubbles_data.append({
#             'bubble_no': int(bubble_no),
#             'panel_no': int(panel_no),
#             'japanese_text': japanese_text,
#             'arabic_text': arabic_text,
#             'coordinates': {
#                 'x1': float(bubble["x"]),
#                 'y1': float(bubble["y"]),
#                 'x2': float(bubble["x"] + bubble["width"]),
#                 'y2': float(bubble["y"] + bubble["height"])
#             }
#         })
#         self.bubble_counter += 1

#     def save_bubble_data_to_json(self, file_path):
#         with open(file_path, 'w', encoding='utf-8') as f:
#             json_data = self.convert_to_native_types(self.bubbles_data)
#             json.dump(json_data, f, ensure_ascii=False, indent=4)

#     def convert_to_native_types(self, d):
#         if isinstance(d, dict):
#             return {k: self.convert_to_native_types(v) for k, v in d.items()}
#         elif isinstance(d, list):
#             return [self.convert_to_native_types(v) for v in d]
#         elif isinstance(d, (np.float32, np.float64)):
#             return float(d)
#         elif isinstance(d, (np.int32, np.int64)):
#             return int(d)
#         else:
#             return d

#     def mark_bubble_as_processed(self, bubble):
#         # Calculate the rectangle coordinates
#         x1 = bubble["x"]
#         y1 = bubble["y"]
#         x2 = x1 + bubble["width"]
#         y2 = y1 + bubble["height"]

#         print(f"Marking bubble as processed and drawing green rectangle at: ({x1}, {y1}, {x2}, {y2})")  # Debug: Print marking coordinates

#         # Draw a green rectangle around the bubble
#         self.canvas.create_rectangle(x1, y1, x2, y2, outline="green", width=2)
#         self.canvas.update_idletasks()  # Ensure the canvas updates

#         # Add to processed bubbles to avoid re-processing
#         self.processed_bubbles.add((x1, y1, x2, y2))

#     def on_mouse_release(self, event):
#         canvas_x = self.canvas.canvasx(event.x)
#         canvas_y = self.canvas.canvasy(event.y)
#         if self.selection_start and self.selection_end:
#             print("Selection Start:", self.selection_start)
#             print("Selection End:", self.selection_end)
#             self.perform_ocr_on_selection(self.selection_start[0], self.selection_start[1], canvas_x, canvas_y)  # <-- Fix indentation here

#     def identify_bubble(self, x, y):
#     # Scale the coordinates
#         scale_x = self.original_width / self.display_width
#         scale_y = self.original_height / self.display_height
#         scaled_x = x * scale_x
#         scaled_y = y * scale_y
#         print(f"Identifying bubble at scaled coordinates: x={scaled_x}, y={scaled_y}")  # Debug: Scaled point

#         for bubble in self.bubbles:
#             print(f"Checking bubble: {bubble}")  # Debug: Checking each bubble
#             if self.bubble_contains_coords(bubble, scaled_x, scaled_y):
#                 print(f"Bubble found: {bubble}")  # Debug: Bubble found
#                 return bubble
#         print(f"No bubble contains the point ({scaled_x}, {scaled_y})")  # Debug: No bubble found
#         return None


#     # Function to identify which panel a bubble belongs to
#     def identify_panel_for_bubble(self, bubble):
#         for panel in self.panels:
#             if self.bubble_within_panel(bubble, panel):
#                 print("Bubble within panel:", panel['panel_no'])
#                 return panel['panel_no']
#         print("No panel found for bubble.") 
#         return 0  # Return 0 if no panel is found

#     # Function to check if a bubble is within a panel
#     def bubble_within_panel(self, bubble, panel):
#         bubble_x1 = bubble["x"]
#         bubble_y1 = bubble["y"]
#         bubble_x2 = bubble_x1 + bubble["width"]
#         bubble_y2 = bubble_y1 + bubble["height"]

#         panel_x1 = panel["x"]
#         panel_y1 = panel["y"]
#         panel_x2 = panel_x1 + panel["width"]
#         panel_y2 = panel_y1 + panel["height"]

#         return (panel_x1 <= bubble_x1 <= panel_x2 and panel_y1 <= bubble_y1 <= panel_y2) and \
#                (panel_x1 <= bubble_x2 <= panel_x2 and panel_y1 <= bubble_y2 <= panel_y2)

#     # Function to convert prediction data to pixel bounding boxes
#     def convert_predictions_to_pixel_bboxes(self, predictions):
#         pixel_bounding_boxes = []
#         panel_no = 1  # Start numbering panels from 1
#         for prediction in predictions["predictions"]:
#             x_center = prediction["x"]
#             y_center = prediction["y"]
#             width = prediction["width"]
#             height = prediction["height"]

#             x_min = x_center - (width / 2)
#             y_min = y_center - (height / 2)

#             # Add panel number for panel predictions
#             if prediction["class"] == "panel":
#                 pixel_bounding_boxes.append({
#                     "panel_no": panel_no,
#                     "x": x_min,
#                     "y": y_min,
#                     "width": width,
#                     "height": height
#                 })
#                 panel_no += 1
#             else:
#                 pixel_bounding_boxes.append({
#                     "x": x_min,
#                     "y": y_min,
#                     "width": width,
#                     "height": height
#                 })
#         return pixel_bounding_boxes

#     def onFrameConfigure(self, event):
#         '''Reset the scroll region to encompass the inner frame'''
#         self.canvas.configure(scrollregion=self.canvas.bbox("all"))

#     def on_closing(self):
#         # Ask user to save JSON file
#         json_path = filedialog.asksaveasfilename(
#             title="Save JSON Data",
#             filetypes=[("JSON files", "*.json"), ("All Files", "*.*")],
#             defaultextension=".json"
#         )
#         if json_path:
#             self.save_bubble_data_to_json(json_path)
#             print(f"Data saved to {json_path}")
#         else:
#             print("JSON save operation cancelled.")

#         # Ask user to save CSV file
#         csv_path = filedialog.asksaveasfilename(
#             title="Save CSV Data",
#             filetypes=[("CSV files", "*.csv"), ("All Files", "*.*")],
#             defaultextension=".csv"
#         )
#         if csv_path:
#             self.save_bubble_data_to_csv(csv_path)
#             print(f"Data saved to {csv_path}")
#         else:
#             print("CSV save operation cancelled.")

#         self.destroy()

#     def save_bubble_data_to_csv(self, file_path):
#         with open(file_path, mode='w', newline='', encoding='utf-8') as file:
#             writer = csv.writer(file)
#             # Update the header to include 'arabic_text'
#             writer.writerow(['bubble_no', 'panel_no', 'japanese_text', 'x1', 'y1', 'x2', 'y2'])
#             # Write bubble data including Arabic text for each bubble
#             for bubble in self.bubbles_data:
#                 writer.writerow([
#                     bubble['bubble_no'],
#                     bubble['panel_no'],
#                     bubble['japanese_text'],
#                     # bubble['arabic_text'],  # Include Arabic text here
#                     bubble['coordinates']['x1'],
#                     bubble['coordinates']['y1'],
#                     bubble['coordinates']['x2'],
#                     bubble['coordinates']['y2']
#                 ])

#     def _create_scrollbar(self, orientation):
#         scroll = tk.Scrollbar(self, orient=orientation,
#                             command=self.canvas.xview if orientation == tk.HORIZONTAL else self.canvas.yview)
#         scroll.pack(side=tk.BOTTOM if orientation == tk.HORIZONTAL else tk.RIGHT, 
#                     fill=tk.X if orientation == tk.HORIZONTAL else tk.Y)
#         if orientation == tk.HORIZONTAL:
#             self.h_scroll = scroll
#             self.canvas.config(xscrollcommand=self.h_scroll.set)
#         else:
#             self.v_scroll = scroll
#             self.canvas.config(yscrollcommand=self.v_scroll.set)
#         return scroll

#     def get_image_dpi(self):
#         with Image.open(self.image_path) as img:  
#             dpi = img.info.get('dpi', (72, 72))  
#         return dpi

#     def identify_panel(self, x1, y1, x2, y2):
#         for panel in self.panels:
#             if self.panel_contains_coords(panel, x1, y1, x2, y2):
#                 print("Panel found:", panel['panel_no'])
#                 return panel['panel_no']
#             print("No panel found for coordinates:", x1, y1, x2, y2)
#         return None

#     @staticmethod
#     def bubble_contains_coords(bubble, x, y):
#         bx1, by1, bx2, by2 = bubble['x'], bubble['y'], bubble['x'] + bubble['width'], bubble['y'] + bubble['height']
#         contains = bx1 <= x <= bx2 and by1 <= y <= by2
#         print(f"Checking if point ({x}, {y}) is within bubble with coordinates: ({bx1}, {by1}, {bx2}, {by2}) -> {contains}")
#         return contains


#     @staticmethod
#     def panel_contains_coords(panel, x1, y1, x2, y2):
#         px1, py1, px2, py2 = panel['x'], panel['y'], panel['x'] + panel['width'], panel['y'] + panel['height']
#         return px1 <= x1 <= px2 and py1 <= y1 <= py2 and px1 <= x2 <= px2 and py1 <= y2 <= py2

# def main():
#     start_page = StartPage()
#     start_page.mainloop()

# if __name__ == "__main__":
#     main()
