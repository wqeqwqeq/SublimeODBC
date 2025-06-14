import sublime_plugin
import sublime
import sqlparse



class SaFormat(sublime_plugin.TextCommand):
    def run(self, edit):
        selectionRegions = self.getSelectionRegions()
        format_style = {
            "keyword_case": "upper",
            "identifier_case": None,
            "strip_comments": False,
            "indent_tabs": False,
            "indent_width": 4,
            "reindent": True,
        }
        for region in selectionRegions:
            textToFormat = self.view.substr(region)
            self.view.replace(edit, region, self.formatSql(textToFormat, format_style))

    def getSelectionRegions(self):
        expandedRegions = []
        if not self.view.sel():
            print("return None")
            return None

        expandTo = "file"

        for region in self.view.sel():
            # if user did not select anything - expand selection,
            # otherwise use the currently selected region
            if region.empty():
                if expandTo in ["file", "view"]:
                    region = sublime.Region(0, self.view.size())
                    # no point in further iterating over selections, just use entire file
                    return [region]

                else:
                    # expand to line
                    region = self.view.line(region)

            # even if we could not expand, avoid adding empty regions
            if not region.empty():
                expandedRegions.append(region)

        return expandedRegions

    def formatSql(self, raw, settings):
        try:
            result = sqlparse.format(raw, **settings)
            return result
        except Exception:
            return None
        
class ExpandSelectionToSemicolon(sublime_plugin.TextCommand):
    def run(self, edit, mode, endstart=None):
        def replace_region(start, end, mode, endstart):

            self.view.sel().clear()
            self.view.sel().add(sublime.Region(start, end))
            for sel in self.view.sel():
                content = self.view.substr(sel)
                if "Done" in content:
                    content = content.replace("Done", " " * len("Done"), 1)
                if "Not     " in content:
                    print("Not here")
                    content = content.replace("Not     ", " " * len("Not Done"), 1)

                print(content, len(content))
                content = list(content)
                num_lst = list(range(start, end))
                # find first non space and non

                for first_non_space_index, word in zip(num_lst, content):
                    if word not in ["\n", " ", " "]:
                        break

            self.view.sel().clear()
            self.view.sel().add(sublime.Region(first_non_space_index, end))
            sel = self.view.sel()[0]
            if mode != "select":
                new_content = self.view.substr(sel)

                spacebtw = endstart - len(new_content) - len(mode) - 1
                spaces = " " * spacebtw

                final = spaces + mode
                print(final)
                self.view.insert(edit, end + 1, final)

                # charlen = len(mode)
                # new_mode = " "*(endstart-charlen)+mode
                # self.view.insert(edit,end+1,new_mode)
                # new_end_point = end+1+len(new_mode)
                # self.view.sel().clear()
                # print(first_non_space_index, end+1,mode)
                self.view.sel().clear()
                self.view.sel().add(first_non_space_index)

        def process_func(cursors, mode, endstart):
            for sel in cursors:
                semicolon = list(map(lambda x: x.begin(), self.view.find_all(";")))
                # print(semicolon, sel, sel.begin(), sel.end())
                # no semicolon in file
                if len(semicolon) == 0:
                    return
                # only one semicolon in entire file
                elif len(semicolon) == 1:
                    replace_region(0, semicolon[0], mode, endstart)
                # currently only support single cursor, not selection cursor with region
                elif len(semicolon) >= 1:
                    print("multiple semi")
                    cursor_begin = sel.begin()
                    cursor_end = sel.end()

                    # only has one cursor
                    # must be on the left side of the semicolon
                    if cursor_begin == cursor_end and cursor_begin + 1 not in semicolon:
                        print(cursor_begin, cursor_end, semicolon)

                        lst = sorted(semicolon + [cursor_begin])
                        idx = lst.index(cursor_begin)
                        # in case cursor begin is the first index, which means there is no semicolon before current cursor
                        if lst[0] == cursor_begin:
                            start = 0
                            end = lst[idx + 1]
                            replace_region(start, end, mode, endstart)
                        # in case btw two ;, start+1 get the right of ;, all the way till the left of second ;
                        else:
                            start = lst[idx - 1]
                            end = lst[idx + 1]
                            replace_region(start + 1, end, mode, endstart)

                return

        # assert mode in ["select","Done","Not Done"],"not exist"
        cursors = self.view.sel()
        process_func(cursors, mode, endstart)