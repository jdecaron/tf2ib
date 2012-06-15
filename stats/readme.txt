TF2 Server Log Parser

by Rusty Fausak
rustyfausak@gmail.com
#clanYoda on mIRC.GameSurge.net
v1.1 jan 4 2008

I give permission to use this package as long as you keep this file and all original
comments intact, and give credit to me as the original author. Do not re-distribute
or re-host any of the source code or files.

Originally hosted on http://www.thursday.com/tf2logger/

Please have a working knowledge of PHP,HTML, and CSS before you begin to edit anything.

YOU MUST MAKE THE DIRECTORY THAT YOU EXTRACT ALL THE FILES INTO WRITEABLE BY THE
SCRIPT! This means 755 or 777 or 775.

The only thing you really need to change is the $sha1_pwd variable in parser.php.
You need to choose your favorite strong password and sha1() it using the PHP sha1
function, and copy paste the output to that variable declaration.

This whole package should be pretty standalone, but due to recent changes in Valve's
logging scheme, some aspects of the parser have gone untested. Also, I currently
just discard all 'position' information, as it is of little use to me.

The parser's main use is for clan matches in TF2, and little interesting information
will be extracted from a normal pub-style server log. I forgot to add in the final
score for each clan, so if you are savvy, go ahead and do that.

The parser creates HTML output that is formatted by CSS. If you make changes to the
parser.php, you will have to re-parse any log that you want updated. You can do this
easily with the functions I have provided in parser.php, assuming you set the sha1
password and understand $_GET variables in PHP. You can make changes to the CSS
file and have it propagate immediatly to all the output (duh).

This parser is by no means perfect, and probably has quite a few bugs still. I am
not a master of PHP either, so if something looks wrong, it very well might be

Thanks for using this, and let me know if you need help or have any comments/suggestions!
Rusty Fausak
rustyfausak@gmail.com