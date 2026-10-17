# Terminal assets

Vendored from the official npm packages `@xterm/xterm@5.5.0` and
`@xterm/addon-fit@0.10.0`. Their MIT license notices are included alongside the assets.
Serving these locally keeps the demo independent of a CDN and does not send terminal
contents to a third-party website.

## Graph canvas

`force-graph.min.js` is vendored from the official npm package `force-graph@1.52.0`
(https://github.com/vasturiano/force-graph). Its MIT license is saved as
`force-graph-LICENSE`. This bundles the force simulation and canvas renderer;
no external CDN or visualization server is used at runtime.

## Project monitor prototype

`project.html` is first-party MidFlight UI code, served here as a standalone,
read-only prototype alongside the existing demo. It is not a third-party package.
