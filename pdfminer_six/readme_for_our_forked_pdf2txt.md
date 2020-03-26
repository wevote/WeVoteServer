**March 25, 2020**

pdf2txt.py is from pdfminer.six==20200124

https://github.com/pdfminer/pdfminer.six

pdfminer.six is a command line tool, that we include through
requirements.txt

pdf2txt.py is the file that contains the main() for pdfminer.six
and has been copied from pdfminer.six version 20200124.

A small modification has been made to our forked version of pdf2txt.py
at about line 167

```
def main(args=None):
    # Begin WeVote Modification to pdf2txt.py copied from pdfminer.six==20200124 on March 29, 2020
    # TODO: as we update pdfminer.six, we might need to update this forked file too
    if __name__ == '__main__':
        import sys
        main(sys.argv[1:])
    # End WeVote Modification

```

This change modifies the way the (previously) command line tool
parses arguments, so it can be directly called from views_extension
