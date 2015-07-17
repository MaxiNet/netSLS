"""
Copyright 2015 Malte Splietker

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""


def indent(text, indentation, indentation_character="\t"):
    """Indents all lines of a string with the given indentation.

    Args:
        text: String to indent.
        indentation: Number of indentation characters to indent.
        indentation_character: indentation character to use
    """
    blank = indentation_character * indentation
    return "\n".join(blank + x for x in text.splitlines())
