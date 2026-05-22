from PIL import Image, ImageDraw, ImageFont

def create_schedule(width, height, classroom, students_class, lesson_start_time, lesson_end_time, subject, teacher, current_time, battery, list_next_lessons):
    row_height = 22
    battery_height = round(battery / 10)
    image = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)

    classroom_font = ImageFont.truetype("Rubik-ExtraBold.ttf", size = 30)
    subject_font = ImageFont.truetype("Rubik-ExtraBold.ttf", size = 60)
    standart_text = ImageFont.truetype("Rubik-Medium.ttf", size = 20)
    italic = ImageFont.truetype("Rubik-LightItalic.ttf", size = 30)
    small_text = ImageFont.truetype("Rubik-Medium.ttf", size = 15)

    def following_lesson(x, y, time, teacher, subject_abb, students_class, note = ""):
        draw.text((x + 5, y), time, font = small_text, fill = (0, 0, 0))
        draw.text((x + (width * 3 // 8) - 10, y), teacher, font = small_text, fill = (0, 0, 0))
        draw.text((x + (width // 2) - 10, y), subject_abb, font = small_text, fill = (0, 0, 0))
        draw.text((x + (width * 5 // 8), y), students_class, font = small_text, fill = (0, 0, 0))
        draw.text((x + (width * 3 // 4), y), note, font = small_text, fill = (255, 0, 0))
        if note == "zrušeno" or note[:8] == "přes. do":
            draw.line(((x, y + 10), ((width * 3 // 4) - 10, y + 10)), width = 2, fill = (255, 0, 0))

    draw.rectangle((0, 0, width, 40), fill = (255, 0, 0))
    draw.text((5, 5), classroom, font = classroom_font, fill = (255, 255, 255))
    draw.text((75, 5), f"aktuálně: {lesson_start_time} - {lesson_end_time}", font = italic, fill = (255, 255, 255))
    
    draw.text((5, 40), subject, font = subject_font, fill = (255, 0, 0))
    draw.text((275, 50), f"třída: {students_class}", font = standart_text, fill = (0, 0, 0))
    draw.text((275, 80), f"učitel: {teacher}", font = standart_text, fill = (0, 0, 0))

    draw.line(((0, 110), (width, 110)), width = 2, fill = (255, 0, 0))

    draw.text((5, 120), "následující hodiny:", font = small_text, fill = (0, 0, 0))
    for i, lesson in enumerate(list_next_lessons):
        following_lesson(0, 140 + i * row_height, f"{lesson[0]} - {lesson[1]}", lesson[2], lesson[3], lesson[4], lesson[5])
    
    draw.text((width - 55, height - 20), current_time, font = small_text, fill = (0, 0, 0))

    draw.rectangle((width - 7, height - 15, width - 2, height - 5), outline = "red", width = 1)
    draw.rectangle((width - 7, height - 15 + (10 - battery_height), width - 2, height - 5), fill = "red")

    image.save("schedule_image.png")

def wbr_colors(source_image):
    colors = [(255, 255, 255), (0, 0, 0), (255, 0, 0)]
    source = Image.open(source_image)
    source = source.resize((800, 480), resample = Image.BILINEAR)
    source = source.convert("RGB")
    width, height = source.size
    new_image = Image.new("RGB", (width, height))
    for i in range(width):
        for j in range(height):
            (r, g, b) = source.getpixel((i, j))
            new_pixel_color = (0, 0, 0)
            lowest_pixel_difference_index = 765
            for color in colors:
                pixel_difference_index = abs(r - color[0]) + abs(g - color[1]) + abs(b - color[2])
                if pixel_difference_index < lowest_pixel_difference_index:
                    lowest_pixel_difference_index = pixel_difference_index
                    new_pixel_color = color
            new_image.putpixel((i, j), new_pixel_color)
    new_image.save("schedule_image.png")

def get_binary_files(source_image):
    source = Image.open(source_image)
    source = source.convert("RGB")
    width, height = source.size
    pixel_data = []
    binary_number = ""
    data_in_file = 0
    for i in range(height):
        for j in range(width):
            (r, g, b) = source.getpixel((j, i))
            if (r, g, b) == (0, 0, 0):
                binary_number += "1"
            else:
                binary_number += "0"
            if len(binary_number) == 8:
                data_in_file += 1
                hex_number = hex(int(binary_number, 2))
                if len(hex_number) == 3:
                    hex_number = hex_number[:2] + "0" + hex_number[2]
                pixel_data.append(int(hex_number, 16))
                binary_number = ""
    binary_data = bytes(pixel_data)
    with open("uploads/black_binary.bin", "wb") as file_black_binary:
        file_black_binary.write(binary_data)
    pixel_data = []
    binary_number = ""
    data_in_file = 0
    for i in range(height):
        for j in range(width):
            (r, g, b) = source.getpixel((j, i))
            if (r, g, b) == (255, 0, 0):
                binary_number += "1"
            else:
                binary_number += "0"
            if len(binary_number) == 8:
                data_in_file += 1
                hex_number = hex(int(binary_number, 2))
                if len(hex_number) == 3:
                    hex_number = hex_number[:2] + "0" + hex_number[2]
                pixel_data.append(int(hex_number, 16))
                binary_number = ""
    binary_data = bytes(pixel_data)
    with open("uploads/red_binary.bin", "wb") as file_red_binary:
        file_red_binary.write(binary_data)
