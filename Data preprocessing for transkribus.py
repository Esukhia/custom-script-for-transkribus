
import math
import re
import itertools  

from shutil import copyfile
from pathlib import Path
from bs4 import BeautifulSoup
from statistics import mean
from collections import defaultdict 


def read_xml(xml):
    '''
    The function returns xml content of transkribus output.
    
    Args:
        xml(.xml file): It is the output of Transkribus OCR model which contains the coordinates and text of
                        recognized box.
    Return:
        xml_content (String):It is the content of .xml file
    
    '''
    with open(xml) as f:
        xml_content = f.read()
    return xml_content


def get_coord(point):
    '''
    This function returns coordinate of a point.
    
    Args:
        point (String): It contain coordinate of a point. Eg : '233,55'
    Return:
        coord (list): It contains x and y coordinate of a point as element of a list for easy access. Eg: [233,55]
    '''
    coord = point.split(',')
    return coord


def get_baseline_length(x1, y1, x2, y2):
    '''
    This function returns distance of baseline.
    '''
    distance = math.sqrt( ((x1-x2)**2)+((y1-y2)**2) )
    return distance


def get_y_avg(coords):
    '''
    This function returns the average y coordinate of a box.
    '''
    ys = []
    for coord in coords:
        point = get_coord(coord)
        ys.append(int(point[1]))
    y_mean = mean(ys)
    return y_mean


def get_line_indicator(coords):
    '''
    This function return y axis coordinate of 
    '''
    ys = []
    for coord in coords:
        point = get_coord(coord)
        ys.append(int(point[1]))
    y_mean = mean(ys)
    if y_mean%100 > 30:
        result = (y_mean//100+1)*100
    else:
        result = (y_mean//100)*100
    return result


def get_poly_coord(poly):
    '''
    This function returns coordinates of polygon.
    '''
    points = poly
    result = []
    for point in points:
        point = point.split(',')
        result.append((int(point[0]),int(point[1])))
    return result


def get_avg_height(poly):
    '''
    This function calculate the average height of the polygon and returns the result.
    '''
    num_points = len(poly)
    num_pairs = num_points//2
    sum_height = 0
    for i in range(num_pairs):
        dif = poly[i][1]-poly[num_points-1 - i][1]
        sum_height += dif
    avg_height = sum_height//num_pairs
    return avg_height 


def get_main_region(regions):
    '''
    This function traverse all the regions recognised by the segmentor and find the largest region by finding
    the region where maximum textLine is found. It return the index of that region.
    '''
    len_lines = []
    for region in regions:
        lines = region.find_all('TextLine')
        len_lines.append(len(lines))
    return len_lines.index(max(len_lines))


def create_box(xml):
    '''
    This function parse the xml file contain. It creates dictionary call boxes which contains text, staring x 
    coordinate of baseline and average y coordinate of baseline.
    
    Args:
        xml (String): Contains the Transkribus output.
    
    Returns:
        boxes (dict): Contains text, staring x coordinate of baseline and average y coordinate of baseline.
    '''
    boxes = {}
    soup = BeautifulSoup(xml, 'xml')
    regions = soup.find_all('TextRegion')
    main_region = get_main_region(regions)
    lines = regions[main_region].find_all('TextLine')
    for i,line in enumerate(lines):
        boxes[f'box{i}'] = {}
        poly_coords = get_poly_coord(line.Coords['points'].split())
        avg_height = get_avg_height(poly_coords)
        baseline_coords = line.Baseline['points'].split() # Extracting all coordinates of baseline points
        start_base_point = get_coord(baseline_coords[0]) # Getting x coordinate of staring point of baseline point
        end_base_point = get_coord(baseline_coords[-1])
        base_y_avg = get_y_avg(baseline_coords) # Getting average of y coordinates of baseline points
        line_indicator = get_line_indicator(baseline_coords)
        boxes[f'box{i}']['bl_start_x'] = int(start_base_point[0])
        boxes[f'box{i}']['bl_start_y'] = int(base_y_avg)
        boxes[f'box{i}']['bl_end_x'] = int(end_base_point[0])
        boxes[f'box{i}']['bl_end_y'] = int(base_y_avg)
        boxes[f'box{i}']['bl_length'] = get_baseline_length(int(start_base_point[0]),base_y_avg,int(end_base_point[0]),base_y_avg)
        boxes[f'box{i}']['avg_height'] = int(avg_height)
        boxes[f'box{i}']['line_indicator'] = int(line_indicator)
    return boxes         


def vertical_sort(boxes):
    result = sorted(boxes.items(), key = lambda x: x[1]['line_indicator'])
    return dict(result)


def horizontal_sort(boxes):
    res = defaultdict(list)
    sorted_box = {}
    for key,box in boxes.items():
        res[box['line_indicator']].append(key)
    res = dict(res)
    for key,re in res.items():
        sub_box = {key: boxes[key] for key in re}
        sorted_sub_box = dict(sorted(sub_box.items(), key = lambda x: x[1]['bl_start_x']))
        sorted_box.update(sorted_sub_box)
    return sorted_box


def line_simplification(sub_box, line_num):
    line = None
    start = min(sub_box.items(), key = lambda x: x[1]['bl_start_x'] )[1]['bl_start_x']
    end = max(sub_box.items(), key = lambda x: x[1]['bl_end_x'] )[1]['bl_end_x']
    longest_baseline = max(sub_box.items(), key = lambda x: x[1]['bl_length'])
    height = longest_baseline[1]['avg_height']
    y_avg = longest_baseline[1]['bl_start_y']
    line_indicator = longest_baseline[1]['line_indicator']
    poly_x1 = start
    poly_y1 = int(y_avg - height*1.25)
    poly_x2 = end
    poly_y2 = int(y_avg - height*1.25)
    poly_x3 = end
    poly_y3 = y_avg + height//2
    poly_x4 = start
    poly_y4 = y_avg + height//2
    baseline_length = get_baseline_length(start,y_avg,end,y_avg)
    if baseline_length >400 and line_indicator != 0:
        line ={
            f'l{line_num}':{
                'bl_points': f'{start},{y_avg} {end},{y_avg}',
            'poly_coord': f'{poly_x4},{poly_y4} {poly_x3},{poly_y3} {poly_x2},{poly_y2} {poly_x1},{poly_y1}'
            }

        }
    return line


def simplification(boxes):
    res = defaultdict(list)
    sorted_box = {}
    for key,box in boxes.items():
        res[box['line_indicator']].append(key)
    res = dict(res)
    line_counter = 0
    for key,re in res.items():
        sub_box = {key: boxes[key] for key in re}
        line = line_simplification(sub_box, line_counter)
        if line:
            sorted_box.update(line)
        line_counter +=1
    return sorted_box


def get_region_coord(xml):
    soup = BeautifulSoup(xml, 'xml')
    regions = soup.find_all('TextRegion')
    main_region = get_main_region(regions)
    poly_coord = regions[main_region].Coords['points']
    return poly_coord


def get_head(xml):
    xml = read_xml(xml)
    lines = xml.splitlines()
    head = ''
    for line in lines:
        if '<ReadingOrder>' in line:
            break
        head += line + '\n'
    region_coord = get_region_coord(xml)
    head += f'<TextRegion id = "r1">\n<Coords points = "{region_coord}"/>\n'
    return head


def serialize_change(sim_box, texts, file_name, head):
    transcribe = ''
#     if len(texts) < len(sim_box):
#         for i in range(len(texts),len(sim_box)):
#             texts.append('')
    result = head
    for i, (line, text) in enumerate(zip(sim_box.items(), texts)):
        poly = line[1]['poly_coord']
        bl = line[1]['bl_points']
        result += f'<TextLine id="r1l{i}">\n'
        result += f'<Coords points="{poly}"/>\n'
        result += f'<Baseline points="{bl}"/>\n'
        result += f'<TextEquiv>\n<Unicode>{texts[i]}</Unicode>\n</TextEquiv>\n</TextLine>\n'
        transcribe += texts[i] + '\n'
    result += f'<TextEquiv>\n<Unicode>{transcribe}</Unicode>\n</TextEquiv>\n</TextRegion>\n</Page>\n</PcGts>'
    f = open(f'./output/page/{file_name}.xml', 'w+')
    f.write(result)
    pass


def get_images(image_path, output_path):
    """Get images.

    Args:
        image_path (path): image path object
    """
    images = [e for e in image_path.rglob('*.jpg')]
    for image in images:
        copyfile(image, output_path / f'{image.stem}.jpg')


def get_res_file(res_path, output_path):
    """Get resource files.

    Args:
        res_path (path): resource path object
    """
    res_files = [e for e in res_path.glob('*.xml')]
    for res_file in res_files:
        copyfile(res_file, output_path / f'{res_file.stem}.xml')


def get_transcript_list(text):
    """Get list of page from transcript text.

    Args:
        text (str): transcript text

    Returns:
        list: list of each page content from the transcript text
    """
    return re.split('\[.+\]', text)[1:]


def get_transcript(text):
    """Get transcript text in a page.

    Args:
        text (str): transcript text of a page

    Returns:
        list: list containing line of transcript from a page
    """
    result = []
    lines = text.splitlines()
    for line in lines:
        if line:
            result.append(line)
    return result


def post_process(pecha_id):
    try:
        layout_path = Path(f'./transkribus_layout_files/{pecha_id}/page')
        resource_path = Path(f'./transkribus_layout_files/{pecha_id}')
    except:
        print('Invalid Pecha id ....')
    layout_files = list(layout_path.iterdir())
    layout_files.sort()
    output_path = Path(f'./postprocessing_output/{pecha_id}/page').mkdir(parents=True, exist_ok=True)
    for i, layout_file in enumerate(layout_files):
        xml = read_xml(layout_file)
        print(layout_file.stem)
        boxes = create_box(xml)
        if boxes:
            vertical_sorted = vertical_sort(boxes)
            sorted_boxes = horizontal_sort(vertical_sorted)
            sim_box = simplification(sorted_boxes)
            sim_box = rm_overlap(sim_box)
            texts = ["" for box in range(len(sim_box))]
            head = get_head(layout_file)
            serialize_change(sim_box, texts, layout_file.stem, head, pecha_id)
    get_images(resource_path, output_path)
    get_res_file(resource_path, output_path)
    print('Output Ready')

if __name__ =="__main__":
    apply_transcript()

