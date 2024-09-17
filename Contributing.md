pull requests are more than welcome, and they are always accepted as long as they abide by the following rules

1. the overhead introduced by whatever feature you add should be worth it: one of odin's design goals is to be as lightweight as possible, not for the end user, but rather for the server side itself
2. KISS: keep it stupid simple, whatever it is you are implementing, no need to make it more advanced than need be
3. no security vulnerabilities: if your code has an obvious security vulnerability, the pull request won't be accepted until it's fixed
4. no download restrictions: don't add any line of code that can be used to restrict certain people from downloading something, any and all files that are hosted on Odin should be available for anyone and everyone
5. no end user analytics: I don't care what advantages it brings, don't bother implementing any form of user analytics, it will be refused
6. no OOP: honestly, OOP just adds more complexity to code, use good old procedural and functional programming, if I see the word "class" anywhere in the code, the request will be refused
7. unless javascript is 100% needed, and can't be done without, don't use javascript, it just adds too much overhead to the end user, and with little user experience improvement
8. if javascript is absolutely 100% necessery for a feature, go ahead and use it, BUT DON'T YOU DARE USE ANY JAVASCRIPT FRAMEWORKS
9. and I'm out of requirements, I'll add more here as the project goes along
