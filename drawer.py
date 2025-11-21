from PIL import Image, ImageDraw, ImageFont
from os import walk

hero_icons = {}
def load_icons():
    for (dirpath, dirnames, filenames) in walk("./icons"):
        for file in filenames:
            if 'fier' in file:
                continue
            try:
                hero_icons[file[:file.find(".")]] = Image.open(dirpath+'/'+file).resize((143,143))
            except Exception as e:
                print(e)

load_icons()


def generate_image(player_names, player_icons, difficulty, time_left):
    img = Image.new('RGBA',[800, 600], "white")

    draw = ImageDraw.Draw(img)
    font= ImageFont.truetype("./Freshman.ttf", size=48)

    for i in range(0, 4):
        background_color = "grey"
        if player_names[i] != "Open":
            if i == 0:
                background_color = "#466ec4"
            elif i == 3:
                background_color = "#4fb46d" 
            else:
                background_color = "#d84444"

        draw.rectangle((0,i*150,600, (i+1)*150), fill=background_color, outline="black", width=4)
        draw.text((170, 150*i + 50), player_names[i], font=font, fill="black")
        if player_icons[i] != "None":
            img.paste(hero_icons[player_icons[i]], (4,4 + i * 150))

    time_text = ""
    if time_left > 1:
        time_text = f"In \n{time_left} hours"
    elif time_left > 0:
        time_text = f"In \n<1 hour"
    else:
        time_text = f"Open\nnow!"

    difficulty_color = "#000000"
    if "contender" in difficulty.lower():
        difficulty_color = "#3373bd"
    elif "adept" in difficulty.lower():
        difficulty_color = "#66c5cc"
    elif "paragon" in difficulty.lower():
        difficulty_color = "#f6cf71"
    elif "champion" in difficulty_color.lower():
        difficulty_color = "#8551e0"
    elif "eternal" in difficulty.lower():
        difficulty_color = "#d42222"


    font= ImageFont.truetype("./Freshman.ttf", size=40)
    draw.rectangle((600,0,800, 600), fill=difficulty_color, outline="black", width=4)
    draw.text((610, 50), text=time_text, fill="black", font=font)
    font= ImageFont.truetype("./Freshman.ttf", size=22)
    draw.text((610, 150), text=difficulty, fill="black", font=font)
    font= ImageFont.truetype("./Freshman.ttf", size=18)
    # draw.text((610, 250), text=timer, font=font, fill="black")

    return img

# player_names = ["testo", "pesto", "Open", "Coval"]
# player_icons = ["helena", "rime", "elarion", "sylvie"]
# img = generate_image(player_names, player_icons, 0)
# img.save('test.png')