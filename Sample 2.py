import svgwrite


# Templates for each element of a price tag, each template uses a different style
# The first allows for description points and the second one is used for discounts.
# The format for each element is tuples of coordinates of the elements, followed by the font size for text.
TEMPLATE_1 = {
    "price": [(470, 360), 142],
    "product_number": [(75, 60), 60],
    "desc_line_1": [(50, 90), 35],
    "desc_line_2": [(50, 125), 35],
    "desc_line 3": [(50, 160), 35],
    "date": [(635, 365), 8],
    "description_extra": [(65, 180), (385, 180), 15],
    "eco_fee": [(50, 360), 20],
    "extra": [(50, 335), 20],
    "price_per_line_1": [(50, 260), 16],
    "price_per": [(50, 300), 40],
    "unit_per": [(131, 260), 16],
    "sell_price": [(560, 258), 15]
}

TEMPLATE_2 = {
    "price": [(470, 360), 142],
    "product_number": [(75, 60), 60],
    "desc_line_1": [(50, 90), 35],
    "desc_line_2": [(50, 125), 35],
    "desc_line 3": [(50, 160), 35],
    "date": [(635, 365), 8],
    "price_per_line_1": [(50, 314), 10],
    "price_per": [(50, 348), 30],
    "discount": [(570, 242), 45],
    "original_price": [(570, 200), 45],
    "expiry": [(300, 242), 15],
    "eco_fee": [(185, 360), 12],
    "savings": [(50, 242), 20],
    "line": [(50, 244), (665, 244)],
    "register": [(465, 260), 15],
    "unit_per": [(50, 323), 10]
}


class PriceTag:

    def __init__(self, product_information: dict, name: str, style=1):
        """
        Class for creating price tags using product information, tags can be exported in an SVG format
        :param product_information: Dictionary containing all relevant product info, must follow specific format
        :param style: Number of which template to use, defaults to 1
        :param name: Name of the output SVG file
        """
        self.info = product_information
        self.dwg = svgwrite.Drawing(f'{name}.svg')
        self.style = style

        # Choose the template based on the style selected
        if self.style == 1:
            self.template = TEMPLATE_1
        elif self.style == 2:
            self.template = TEMPLATE_2

        self.create_tag()

    def create_tag(self):
        """
        Creates the elements of the price tag, iterates through all the product information
        and adds it to the SVG based on the chosen templates style
        """
        for t in self.info.keys():
            if self.info[t] and t in self.template.keys():
                # Default font and weight.
                font = "serif"
                weight = "normal"

                if t == "price":
                    # Add the text above the price based on the style chosen
                    if self.style == 2:
                        self.add_text("PRICE AT REGISTER",
                                      self.template["register"][0],
                                      self.template["register"][1])
                    else:
                        self.add_text("SELL PRICE",
                                      self.template["sell_price"][0],
                                      self.template["sell_price"][1])

                    # Scales the location of the price based on it's length
                    coords = (self.template[t][0][0] - (len(self.info[t].split(".")[0] * 70)),
                              self.template[t][0][1])
                    font_size = self.template[t][1]
                    weight = "bold"

                elif t == "price_per":
                    # add a box around the text if the discount style was chosen
                    if self.style == 2:
                        self.dwg.add(self.dwg.rect((45, 305), (100, 46), stroke="black", fill="none", stroke_width=0.5))
                        self.dwg.add(self.dwg.line((45, 325), (145, 325), stroke="black", stroke_width=0.5))

                    self.add_text("PRICE PER",
                                  self.template["price_per_line_1"][0],
                                  self.template["price_per_line_1"][1])

                    coords = self.template[t][0]
                    font_size = self.template[t][1]

                elif t == "description_extra":
                    for x in range(len(self.info[t])):
                        # Calculate the coordinates of each point in the extra description, alternates between left
                        # and right sides to place text
                        if (x + 1) % 2 == 0:
                            x_coord = self.template[t][1][0]
                            y_coord = self.template[t][1][1] + (x * 9) - 9
                        else:
                            x_coord = self.template[t][0][0]
                            y_coord = self.template[t][0][1] + x * 9

                        self.add_text(f"• {self.info[t][x]}", (x_coord, y_coord), self.template[t][2])
                    continue

                elif t == "discount":
                    # Draw a line across the tag
                    self.dwg.add(self.dwg.line(self.template["line"][0],
                                               self.template["line"][1],
                                               stroke="black",
                                               stroke_width=1))

                    self.add_text("Instant Savings",
                                  self.template["savings"][0],
                                  self.template["savings"][1],
                                  weight="bold",
                                  font="sans-serif")

                    # Scales the location of the discount based on the length
                    coords = (self.template[t][0][0] - (len(self.info[t].split(".")[0] * 15)),
                              self.template[t][0][1])
                    font_size = self.template[t][1]
                    font = "sans-serif"

                elif t == "original_price":
                    # Scales the location of the original price based on the length
                    coords = (self.template[t][0][0] - (len(self.info[t].split(".")[0] * 15)),
                              self.template[t][0][1])
                    font_size = self.template[t][1]
                    font = "sans-serif"

                else:
                    coords = self.template[t][0]
                    font_size = self.template[t][1]

                self.add_text(self.info[t], coords=coords, font_size=font_size, weight=weight, font=font)

    def add_text(self, text, coords, font_size, weight="normal", font="serif"):
        """
        Function for adding text to the SVG Canvas
        :param text: Text to be added
        :param coords: Location to add the text, (x, y) format
        :param font_size: Size of the text
        :param weight: Add bold, italics, etc
        :param font: Style of font to use
        """
        self.dwg.add(self.dwg.text(text,
                                   insert=coords,
                                   stroke='none',
                                   fill=svgwrite.rgb(15, 15, 15, '%'),
                                   font_size=f'{font_size}px',
                                   font_weight=weight,
                                   font_family=font))

    def export_svg(self):
        """
        Saves the created tag
        """
        self.dwg.save()
