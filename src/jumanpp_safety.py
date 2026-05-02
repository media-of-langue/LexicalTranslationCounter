def _needs_comment_marker_escape(text):
    return text.lstrip().startswith("#")


def analyze_jumanpp(juman, text):
    if not _needs_comment_marker_escape(text):
        return juman.analysis(text).mrph_list()

    # Juman++ treats lines starting with '#' as comments and does not emit EOS.
    # pyknp strips leading spaces before sending input, so use a non-whitespace
    # sentinel and remove only that artificial token from the parsed result.
    mrph_list = juman.analysis("\\" + text).mrph_list()
    if mrph_list and mrph_list[0].midasi == "\\":
        return mrph_list[1:]
    return mrph_list
