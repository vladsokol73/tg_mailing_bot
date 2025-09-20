import json
import random
import yaml
import numpy as np
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import shutil

BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR.parent / "static" / "config.yaml"

# Пути к шаблонам изображений для разных стран
TEMPLATE_PATHS = {
    "lkr": BASE_DIR.parent / "static" / "lkr.png",
    "pkr": BASE_DIR.parent / "static" / "pkr.png",
    "uzs": BASE_DIR.parent / "static" / "uzs.png",
    "pen": BASE_DIR.parent / "static" / "pen.png",  # Добавлен шаблон для Перу
    "kgs": BASE_DIR.parent / "static" / "kgs.png"
}

# Пути к шаблонам fail-изображений для разных стран
TEMPLATE_FAIL_PATHS = {
    "lkr": BASE_DIR.parent / "static" / "en_fail.png",
    "pkr": BASE_DIR.parent / "static" / "en_fail.png",
    "uzs": BASE_DIR.parent / "static" / "uzs_fail.png",
    "pen": BASE_DIR.parent / "static" / "pen_fail.png",  # Добавлен fail-шаблон для Перу
    "kgs": BASE_DIR.parent / "static" / "en_fail.png",
}

# Для обратной совместимости
BASE_IMAGE_PATH = BASE_DIR.parent / "static" / "base.png"
BASE_FAIL_IMAGE_PATH = BASE_DIR.parent / "static" / "base_fail.png"


def load_config():
    """Load configuration from YAML file"""
    with open(CONFIG_PATH, 'r') as f:
        return yaml.safe_load(f)


def generate_random_number():
    """Generate random number in format 9.99x"""
    config = load_config()
    ranges = config['generation_settings']['number_ranges']
    
    first_num = str(random.randint(ranges['first_number']['min'], ranges['first_number']['max']))
    second_num = str(random.randint(ranges['second_number']['min'], ranges['second_number']['max'])).zfill(2)
    return f"{first_num}.{second_num}x"


def parse_number(number_str):
    """Parse number from format 9.99x to float"""
    return float(number_str[:-1])


def format_subtracted_number(number):
    """Format subtracted number to string with 'x' suffix"""
    return f"{number:.2f}x"


def format_multiplied_number(number):
    """Format multiplied number with two decimal places and thousands separators
    
    Args:
        number (float): Number to format
        
    Returns:
        str: Formatted number with commas as thousands separators
    """
    # Форматируем число с двумя десятичными знаками и разделителями тысяч
    return f"{number:,.2f}"


def add_noise(img, intensity=6):
    """Добавляет шум на изображение"""
    # Конвертируем в numpy array
    img_array = np.array(img)
    
    # Генерируем шум
    noise = np.random.randint(-intensity, intensity + 1, img_array.shape)
    
    # Добавляем шум к изображению
    noisy_img = img_array + noise
    
    # Обрезаем значения до допустимого диапазона
    noisy_img = np.clip(noisy_img, 0, 255)
    
    # Конвертируем обратно в изображение
    return Image.fromarray(noisy_img.astype('uint8'))


def get_text_position(img_width, img_height, text_width, text_height, position_config):
    """Calculate text position based on configuration"""
    if position_config['type'] == 'center':
        return ((img_width - text_width) // 2,
                (img_height - text_height) // 2)
    else:  # custom position
        x = int((position_config['x_percent'] / 100) * img_width - text_width / 2)
        y = int((position_config['y_percent'] / 100) * img_height - text_height / 2)
        return (x, y)


def draw_text_with_shadow(draw, img, text, position, font, color, shadow_config):
    """Draw text with shadow effect"""
    if shadow_config and shadow_config.get('enabled', False):
        # Создаем новое изображение для тени
        shadow_img = Image.new('RGBA', img.size, (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow_img)
        
        # Рисуем текст тени
        shadow_color = tuple(shadow_config['color'])
        offset_x, offset_y = shadow_config['offset']
        shadow_pos = (position[0] + offset_x, position[1] + offset_y)
        shadow_draw.text(shadow_pos, text, font=font, fill=shadow_color)
        
        # Применяем размытие к тени
        if shadow_config.get('blur', 0) > 0:
            shadow_img = shadow_img.filter(ImageFilter.GaussianBlur(shadow_config['blur']))
        
        # Накладываем тень на основное изображение
        img.paste(Image.alpha_composite(img, shadow_img))
    
    # Рисуем основной текст
    draw.text(position, text, font=font, fill=color)


def draw_text(draw, img, text, font_settings, position_config):
    """Draw text using provided configuration"""
    try:
        # Получаем путь к шрифту относительно BASE_DIR
        font_path = BASE_DIR.parent / "static" / font_settings['path']
        font = ImageFont.truetype(str(font_path), font_settings['size'])
    except Exception as e:
        print(f"Warning: Could not load font {font_path}: {e}")
        font = ImageFont.load_default()
    
    # Calculate text position
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Get position from config
    x, y = get_text_position(img.width, img.height, text_width, text_height, position_config)
    
    # Get color and shadow settings
    color = tuple(font_settings['color'])
    shadow_config = font_settings.get('shadow')
    
    # Draw text with or without shadow
    draw_text_with_shadow(draw, img, text, (x, y), font, color, shadow_config)


def process_numbers(main_number_str, config, bet_amount=0):
    """Process numbers for image generation
    
    Args:
        main_number_str (str): The main number in format '9.99x'
        config (dict): Configuration settings
        bet_amount (int, optional): Bet amount to use for multiplied number. Defaults to 0.
    """
    main_number = parse_number(main_number_str)
    
    # Generate subtracted_number according to new rules:
    # 1. Never less than 1.00x
    # 2. Must be less than or equal to main_number
    # 3. 5/7 signals should be between 1.50x and 2.00x (if possible)
    
    # Определяем максимально возможное значение для subtracted_value (не больше main_number)
    max_subtracted = min(main_number, 3.00)  # Не больше main_number и не больше 3.00
    min_subtracted = 1.00  # Минимальное значение всегда 1.00
    
    # Если максимальное значение меньше минимального, используем минимальное
    if max_subtracted < min_subtracted:
        max_subtracted = min_subtracted
    
    # Определяем диапазоны с учетом ограничения по main_number
    range_1_min = min_subtracted
    range_1_max = min(1.50, max_subtracted)
    
    range_2_min = 1.50
    range_2_max = min(2.00, max_subtracted)
    
    range_3_min = 2.00
    range_3_max = max_subtracted
    
    # Determine which range to use based on probability (5/7 chance for 1.50-2.00 range if possible)
    range_selector = random.random()
    
    # Проверяем, возможно ли использовать предпочтительный диапазон (1.50-2.00)
    if range_2_min < range_2_max and range_selector < 5/7:  # 5/7 probability (approximately 71.4%)
        # Generate between 1.50x and min(2.00, max_subtracted)
        subtracted_value = random.uniform(range_2_min, range_2_max)
    else:  # 2/7 probability или если предпочтительный диапазон невозможен
        # Выбираем между двумя другими диапазонами, если они доступны
        if range_1_min < range_1_max and (range_3_min >= range_3_max or random.random() < 0.5):
            # Используем диапазон 1.00-1.50 (если возможно)
            subtracted_value = random.uniform(range_1_min, range_1_max)
        elif range_3_min < range_3_max:
            # Используем диапазон 2.00-3.00 (если возможно)
            subtracted_value = random.uniform(range_3_min, range_3_max)
        else:
            # Если ни один из диапазонов не доступен, используем все доступное пространство
            subtracted_value = random.uniform(min_subtracted, max_subtracted)
    
    subtracted_number = format_subtracted_number(subtracted_value)
    # Округляем коэффициент до двух знаков после запятой для расчёта выигрыша
    rounded_subtracted = round(float(subtracted_number.replace('x', '')), 2)
    
    # Если указана сумма ставки, используем округлённый коэффициент для расчета умноженного числа
    if bet_amount > 0:
        multiplied = rounded_subtracted * bet_amount
    else:
        # Используем стандартный множитель из конфига
        final_multiplier = random.choice(config['multiplied_number']['multipliers'])
        multiplied = subtracted_value * final_multiplier
    
    # Форматируем число с двумя десятичными знаками и разделителями тысяч
    multiplied_number = format_multiplied_number(multiplied)
    
    return {
        "main_number": main_number_str,
        "subtracted_number": subtracted_number,
        "multiplied_number": multiplied_number
    }


class ImageGenerator:
    def __init__(self):
        self.config = load_config()
        self.output_dir = BASE_DIR.parent / "output"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.fail_config = self.config['fail_image']  # Используем настройки из конфига

    def generate_normal_image(self, bet_amount=0, template="lkr"):
        """Generate a normal image with numbers
        
        Args:
            bet_amount (int, optional): Bet amount to use for multiplied number. Defaults to 0.
            template (str, optional): Template to use for image generation. Defaults to "lkr".
                                     Available options: "lkr" (Шри-Ланка), "pkr" (Пакистан), 
                                     "uzs" (Узбекистан), "pen" (Перу).
        """
        try:
            # Generate main number
            main_number_str = generate_random_number()
            
            # Process numbers with bet amount
            data = process_numbers(main_number_str, self.config, bet_amount)
            
            # Determine which template to use
            if template in TEMPLATE_PATHS:
                image_path = TEMPLATE_PATHS[template]
            else:
                # Fallback to default template if specified template doesn't exist
                image_path = BASE_IMAGE_PATH
                
            # Open the base image and convert to RGBA
            img = Image.open(image_path).convert('RGBA')
            draw = ImageDraw.Draw(img)
            
            # Draw main number
            draw_text(draw, img, data['main_number'],
                     self.config['main_number']['font_settings'],
                     self.config['main_number']['position'])
            
            # Draw subtracted number
            draw_text(draw, img, data['subtracted_number'],
                     self.config['subtracted_number']['font_settings'],
                     self.config['subtracted_number']['position'])
            
            # Draw multiplied number
            draw_text(draw, img, data['multiplied_number'],
                     self.config['multiplied_number']['font_settings'],
                     self.config['multiplied_number']['position'])
            
            # Add noise
            img = add_noise(img, intensity=3)
            
            # Save image
            filename = f"{datetime.now().strftime('%d_%m_%y')}_{main_number_str}.png"
            output_path = self.output_dir / filename
            img.save(output_path)
            
            # Save YAML data
            yaml_path = output_path.with_suffix('.yaml')
            yaml_data = {
                'main_number': data['main_number'],
                'subtracted_number': data['subtracted_number'],
                'multiplied_number': data['multiplied_number']
            }
            with open(yaml_path, 'w', encoding='utf-8') as f:
                yaml.dump(yaml_data, f, allow_unicode=True)
            
            return output_path, data
            
        except Exception as e:
            print(f"Error generating normal image: {e}")
            raise

    def generate_fail_image(self, bet_amount=0, template="lkr"):
        """Generate a fail image with swapped main and subtracted numbers
        
        Args:
            bet_amount (int, optional): Bet amount to use for multiplied number. Defaults to 0.
            template (str, optional): Template to use for image generation. Defaults to "lkr".
                                     Available options: "lkr" (Шри-Ланка), "pkr" (Пакистан), 
                                     "uzs" (Узбекистан), "pen" (Перу).
        """
        try:
            # Сначала генерируем main_number и subtracted_number как для обычного изображения
            main_number_str = generate_random_number()
            data_normal = process_numbers(main_number_str, self.config, bet_amount)
            # Меняем местами main_number и subtracted_number
            fail_main_number = data_normal['subtracted_number']  # теперь это основной (больший)
            fail_subtracted_number = data_normal['main_number']  # теперь это вычитаемый (меньший)
            # Для fail-изображения multiplied_number всегда 'fail', независимо от суммы ставки
            multiplied_number = 'fail'
            
            # Определяем, какой шаблон использовать
            if template in TEMPLATE_FAIL_PATHS:
                image_path = TEMPLATE_FAIL_PATHS[template]
            else:
                # Используем шаблон по умолчанию, если указанный шаблон не существует
                image_path = BASE_FAIL_IMAGE_PATH
                
            # Открываем fail image
            img = Image.open(image_path).convert('RGBA')
            draw = ImageDraw.Draw(img)
            # Формируем данные для YAML и отрисовки
            data = {
                'main_number': fail_main_number,
                'subtracted_number': fail_subtracted_number,
                'multiplied_number': multiplied_number
            }
            font_settings = self.fail_config['font_settings']
            position = self.fail_config['position']
            # Draw main number
            draw_text(draw, img, data['main_number'], font_settings, position)
            # Add noise
            img = add_noise(img, intensity=3)
            # Save image
            filename = f"{datetime.now().strftime('%d_%m_%y')}_{main_number_str}_fail.png"
            output_path = self.output_dir / filename
            img.save(output_path)
            # Save YAML data
            yaml_path = output_path.with_suffix('.yaml')
            with open(yaml_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, allow_unicode=True)
            return output_path, data
        except Exception as e:
            print(f"Error generating fail image: {e}")
            raise

    def generate_images(self, count=5, bet_amount=0, template="lkr"):
        """Generate multiple images with one fail image
        
        Args:
            count (int, optional): Number of images to generate. Defaults to 5.
            bet_amount (int, optional): Bet amount to use for multiplied number. Defaults to 0.
            template (str, optional): Template to use for image generation. Defaults to "lkr".
                                     Available options: "lkr" (Шри-Ланка), "pkr" (Пакистан), 
                                     "uzs" (Узбекистан), "pen" (Перу).
        """
        try:
            # Выбираем случайную позицию для fail изображения
            fail_position = random.randint(0, count-1)
            
            # Проверяем, что шаблон существует, иначе используем по умолчанию
            if template not in TEMPLATE_PATHS:
                template = "lkr"  # Используем шаблон по умолчанию
                
            images = []
            data_list = []
            
            for i in range(count):
                if i == fail_position:
                    # Генерируем fail изображение с использованием суммы ставки и выбранного шаблона
                    image_path, image_data = self.generate_fail_image(bet_amount, template)
                else:
                    # Генерируем обычное изображение с использованием суммы ставки и выбранного шаблона
                    image_path, image_data = self.generate_normal_image(bet_amount, template)
                
                images.append(image_path)
                data_list.append(image_data)
            
            return images, data_list
            
        except Exception as e:
            print(f"Error generating multiple images: {e}")
            raise
