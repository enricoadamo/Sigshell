# Topic update email draft

**Status:** Draft for Enrico and Marco to review. Not sent.

**Subject:** Update on our Software Engineering project

Dear Professor,

For our Software Engineering project, we chose `sigscores`, an existing R
library that calculates gene signature scores from gene expression data. We
are building Sigshell to make this analysis easier for computational
biologists who would otherwise need to write R code.

Our submitted topic proposed a plain-English interface: a researcher would
describe an analysis to an AI client, which would call `sigscores` through a
Model Context Protocol (MCP) server. After discussing the idea with Professor
Buffa, a co-author of the library, and Giosuè Moscato, we concluded that a
local web application is the stronger solution for this well-defined workflow.
It guides users through input checks, method selection, results, and export of
reproducible R code.

Would it be acceptable for our final submission to focus **only on the web
application**, leaving the MCP interface outside the project scope?

Best regards,  
Enrico Adamo and Marco Riva
