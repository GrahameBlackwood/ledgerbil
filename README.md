# ledgerbil

A small rodent-like program for working with ledger-cli journals.

Hi! I'm a personal finance enthusiast. Keeping all my numbers organized and analyzable has always been a soothing and reassuring activity for me. I used Microsoft Money from 1995 to 2007, KMyMoney from 2007 to 2012, and now I've switched once again to "Ledger."

I hope this will be my last money program. It's wonderful:

http://www.ledger-cli.org/

But it only *reads* financial data from a journal. You have to provide your own tools for working with the file. At a minimum, all you need is a text editor. I'm using Sublime Text to manage my journal, and with syntax highlighting and regular expressions, it handles the job well.

But I'd like to automate the handling of recurring transactions, with a **scheduler**, and it might be nice to have a tool to speed up statement **reconciliations**, and so on. I imagine it will be fun to do all this myself, using python. I'll be taking my time at it since I can manage indefinitely with just Sublime Text.

So far, **the program will sort an input file** by transaction date. (Woo hoo!) I intend to go overboard with unit testing. If ledger-cli is my "forever money program," then I want to be able to trust the tools I build to work with it.

I don't expect that there will be wide interest in this program, but if you *do* want to use it, that would be awesome. My first goal is to properly handle the subset of ledger-cli that I'm actually using, but I'm open to building it out if asked, and if I can manage it within the limitations of my time and skills.

It's early and things may change widely as I find a path. There will be a way to specify an output file, but for now it just prints to stdout. Using argparse, here are all of the exciting features and options:

## --help

    usage: ledgerbil.py [-h] -f FILE [-s]
    
    optional arguments:
      -h, --help            show this help message and exit
      -f FILE, --file FILE  ledger file to be processed
      -s, --sort            sort the file by transaction date
