import random
import string

from django.db import connection, reset_queries


def randomString(stringLength=8):
    """Generate a random string of fixed length """
    letters = string.ascii_lowercase
    return "".join(random.sample(letters, stringLength))


def num_queries(reset=True, string_marker=None):
    """
    Prints number of db queries. Used for minimizing db hits, put this wherever you want a tally.
    """
    if string_marker:
        print(string_marker, ": ", str(len(connection.queries)))
    else:
        print(len(connection.queries))
    if reset:
        reset_queries()


def snake_case_to_title_text(snake_case_string):
    """
    input: 'image_url'
    output: 'Image Url'
    """
    snake_list = snake_case_string.split("_")
    return " ".join([x.title() for x in snake_list])


def text_to_snake_case(text_string):
    """
    input: 'Image Url'
    output: 'image_url'
    """
    text_list = text_string.split()
    return "_".join([x.lower() for x in text_list])
