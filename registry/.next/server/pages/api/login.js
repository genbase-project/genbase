"use strict";
/*
 * ATTENTION: An "eval-source-map" devtool has been used.
 * This devtool is neither made for production nor for readable output files.
 * It uses "eval()" calls to create a separate source file with attached SourceMaps in the browser devtools.
 * If you are trying to read the output file, select a different devtool (https://webpack.js.org/configuration/devtool/)
 * or disable the default devtool with "devtool: false".
 * If you are looking for production-ready output files, see mode: "production" (https://webpack.js.org/configuration/mode/).
 */
(() => {
var exports = {};
exports.id = "pages/api/login";
exports.ids = ["pages/api/login"];
exports.modules = {

/***/ "firebase/app":
/*!*******************************!*\
  !*** external "firebase/app" ***!
  \*******************************/
/***/ ((module) => {

module.exports = require("firebase/app");

/***/ }),

/***/ "next-absolute-url":
/*!************************************!*\
  !*** external "next-absolute-url" ***!
  \************************************/
/***/ ((module) => {

module.exports = require("next-absolute-url");

/***/ }),

/***/ "next-firebase-auth":
/*!*************************************!*\
  !*** external "next-firebase-auth" ***!
  \*************************************/
/***/ ((module) => {

module.exports = require("next-firebase-auth");

/***/ }),

/***/ "(api)/./pages/api/login.js":
/*!****************************!*\
  !*** ./pages/api/login.js ***!
  \****************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

eval("__webpack_require__.r(__webpack_exports__);\n/* harmony export */ __webpack_require__.d(__webpack_exports__, {\n/* harmony export */   \"default\": () => (__WEBPACK_DEFAULT_EXPORT__)\n/* harmony export */ });\n/* harmony import */ var next_firebase_auth__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! next-firebase-auth */ \"next-firebase-auth\");\n/* harmony import */ var next_firebase_auth__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(next_firebase_auth__WEBPACK_IMPORTED_MODULE_0__);\n/* harmony import */ var _utils_initAuth__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! ../../utils/initAuth */ \"(api)/./utils/initAuth.js\");\n\n\n(0,_utils_initAuth__WEBPACK_IMPORTED_MODULE_1__[\"default\"])();\nconst handler = async (req, res)=>{\n    try {\n        // Including unused return value to demonstrate codemod\n        // eslint-disable-next-line no-unused-vars, @typescript-eslint/no-unused-vars\n        const { user } = await (0,next_firebase_auth__WEBPACK_IMPORTED_MODULE_0__.setAuthCookies)(req, res);\n    } catch (e) {\n        // eslint-disable-next-line no-console\n        console.error(e);\n        return res.status(500).json({\n            error: \"Unexpected error.\"\n        });\n    }\n    return res.status(200).json({\n        status: true\n    });\n};\n/* harmony default export */ const __WEBPACK_DEFAULT_EXPORT__ = (handler);\n//# sourceURL=[module]\n//# sourceMappingURL=data:application/json;charset=utf-8;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiKGFwaSkvLi9wYWdlcy9hcGkvbG9naW4uanMiLCJtYXBwaW5ncyI6Ijs7Ozs7OztBQUFtRDtBQUNSO0FBRTNDQywyREFBUUE7QUFFUixNQUFNQyxVQUFVLE9BQU9DLEtBQUtDO0lBQzFCLElBQUk7UUFDRix1REFBdUQ7UUFDdkQsNkVBQTZFO1FBQzdFLE1BQU0sRUFBRUMsSUFBSSxFQUFFLEdBQUcsTUFBTUwsa0VBQWNBLENBQUNHLEtBQUtDO0lBQzdDLEVBQUUsT0FBT0UsR0FBRztRQUNWLHNDQUFzQztRQUN0Q0MsUUFBUUMsS0FBSyxDQUFDRjtRQUNkLE9BQU9GLElBQUlLLE1BQU0sQ0FBQyxLQUFLQyxJQUFJLENBQUM7WUFBRUYsT0FBTztRQUFvQjtJQUMzRDtJQUNBLE9BQU9KLElBQUlLLE1BQU0sQ0FBQyxLQUFLQyxJQUFJLENBQUM7UUFBRUQsUUFBUTtJQUFLO0FBQzdDO0FBRUEsaUVBQWVQLE9BQU9BLEVBQUEiLCJzb3VyY2VzIjpbIndlYnBhY2s6Ly9yZWdpc3RyeS8uL3BhZ2VzL2FwaS9sb2dpbi5qcz9hZTg4Il0sInNvdXJjZXNDb250ZW50IjpbImltcG9ydCB7IHNldEF1dGhDb29raWVzIH0gZnJvbSAnbmV4dC1maXJlYmFzZS1hdXRoJ1xuaW1wb3J0IGluaXRBdXRoIGZyb20gJy4uLy4uL3V0aWxzL2luaXRBdXRoJ1xuXG5pbml0QXV0aCgpXG5cbmNvbnN0IGhhbmRsZXIgPSBhc3luYyAocmVxLCByZXMpID0+IHtcbiAgdHJ5IHtcbiAgICAvLyBJbmNsdWRpbmcgdW51c2VkIHJldHVybiB2YWx1ZSB0byBkZW1vbnN0cmF0ZSBjb2RlbW9kXG4gICAgLy8gZXNsaW50LWRpc2FibGUtbmV4dC1saW5lIG5vLXVudXNlZC12YXJzLCBAdHlwZXNjcmlwdC1lc2xpbnQvbm8tdW51c2VkLXZhcnNcbiAgICBjb25zdCB7IHVzZXIgfSA9IGF3YWl0IHNldEF1dGhDb29raWVzKHJlcSwgcmVzKVxuICB9IGNhdGNoIChlKSB7XG4gICAgLy8gZXNsaW50LWRpc2FibGUtbmV4dC1saW5lIG5vLWNvbnNvbGVcbiAgICBjb25zb2xlLmVycm9yKGUpXG4gICAgcmV0dXJuIHJlcy5zdGF0dXMoNTAwKS5qc29uKHsgZXJyb3I6ICdVbmV4cGVjdGVkIGVycm9yLicgfSlcbiAgfVxuICByZXR1cm4gcmVzLnN0YXR1cygyMDApLmpzb24oeyBzdGF0dXM6IHRydWUgfSlcbn1cblxuZXhwb3J0IGRlZmF1bHQgaGFuZGxlclxuIl0sIm5hbWVzIjpbInNldEF1dGhDb29raWVzIiwiaW5pdEF1dGgiLCJoYW5kbGVyIiwicmVxIiwicmVzIiwidXNlciIsImUiLCJjb25zb2xlIiwiZXJyb3IiLCJzdGF0dXMiLCJqc29uIl0sInNvdXJjZVJvb3QiOiIifQ==\n//# sourceURL=webpack-internal:///(api)/./pages/api/login.js\n");

/***/ }),

/***/ "(api)/./utils/initAuth.js":
/*!***************************!*\
  !*** ./utils/initAuth.js ***!
  \***************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

eval("__webpack_require__.r(__webpack_exports__);\n/* harmony export */ __webpack_require__.d(__webpack_exports__, {\n/* harmony export */   \"default\": () => (__WEBPACK_DEFAULT_EXPORT__)\n/* harmony export */ });\n/* harmony import */ var firebase_app__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! firebase/app */ \"firebase/app\");\n/* harmony import */ var firebase_app__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(firebase_app__WEBPACK_IMPORTED_MODULE_0__);\n/* harmony import */ var next_firebase_auth__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! next-firebase-auth */ \"next-firebase-auth\");\n/* harmony import */ var next_firebase_auth__WEBPACK_IMPORTED_MODULE_1___default = /*#__PURE__*/__webpack_require__.n(next_firebase_auth__WEBPACK_IMPORTED_MODULE_1__);\n/* harmony import */ var next_absolute_url__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! next-absolute-url */ \"next-absolute-url\");\n/* harmony import */ var next_absolute_url__WEBPACK_IMPORTED_MODULE_2___default = /*#__PURE__*/__webpack_require__.n(next_absolute_url__WEBPACK_IMPORTED_MODULE_2__);\n/* globals window */ \n\n\nconst TWELVE_DAYS_IN_MS = 12 * 60 * 60 * 24 * 1000;\nconst initAuth = ()=>{\n    // Initialize Firebase.\n    const firebaseClientInitConfig = {\n        apiKey: \"AIzaSyCb-_vuseCqF0eo6GSS5vdcj8qADwYO24k\",\n        authDomain: \"hivon-ai.firebaseapp.com\",\n        databaseURL: \"https://hivon-ai.firebaseio.com\",\n        projectId: \"hivon-ai\",\n        storageBucket: \"hivon-ai.firebasestorage.app\"\n    };\n    (0,firebase_app__WEBPACK_IMPORTED_MODULE_0__.initializeApp)(firebaseClientInitConfig);\n    // Initialize next-firebase-auth.\n    (0,next_firebase_auth__WEBPACK_IMPORTED_MODULE_1__.init)({\n        debug: true,\n        // This demonstrates setting a dynamic destination URL when\n        // redirecting from app pages. Alternatively, you can simply\n        // specify `authPageURL: '/auth-ssr'`.\n        authPageURL: ({ ctx })=>{\n            const isServerSide = \"undefined\" === \"undefined\";\n            const origin = isServerSide ? next_absolute_url__WEBPACK_IMPORTED_MODULE_2___default()(ctx.req).origin : window.location.origin;\n            const destPath =  true ? ctx.resolvedUrl : 0;\n            const destURL = new URL(destPath, origin);\n            return `/auth-ssr?destination=${encodeURIComponent(destURL)}`;\n        },\n        // This demonstrates setting a dynamic destination URL when\n        // redirecting from auth pages. Alternatively, you can simply\n        // specify `appPageURL: '/'`.\n        appPageURL: ({ ctx })=>{\n            const isServerSide = \"undefined\" === \"undefined\";\n            const origin = isServerSide ? next_absolute_url__WEBPACK_IMPORTED_MODULE_2___default()(ctx.req).origin : window.location.origin;\n            const params = isServerSide ? new URL(ctx.req.url, origin).searchParams : new URLSearchParams(window.location.search);\n            const destinationParamVal = params.get(\"destination\") ? decodeURIComponent(params.get(\"destination\")) : undefined;\n            // By default, go to the index page if the destination URL\n            // is invalid or unspecified.\n            let destURL = \"/\";\n            if (destinationParamVal) {\n                // Verify the redirect URL host is allowed.\n                // https://owasp.org/www-project-web-security-testing-guide/v41/4-Web_Application_Security_Testing/11-Client_Side_Testing/04-Testing_for_Client_Side_URL_Redirect\n                const allowedHosts = [\n                    \"localhost:3000\",\n                    \"nfa-example.vercel.app\",\n                    \"nfa-example-git-v1x-gladly-team.vercel.app\"\n                ];\n                const allowed = allowedHosts.indexOf(new URL(destinationParamVal).host) > -1;\n                if (allowed) {\n                    destURL = destinationParamVal;\n                } else {\n                    // eslint-disable-next-line no-console\n                    console.warn(`Redirect destination host must be one of ${allowedHosts.join(\", \")}.`);\n                }\n            }\n            return destURL;\n        },\n        loginAPIEndpoint: \"/api/login\",\n        logoutAPIEndpoint: \"/api/logout\",\n        firebaseAdminInitConfig: {\n            credential: {\n                projectId: \"hivon-ai\",\n                clientEmail: process.env.FIREBASE_CLIENT_EMAIL,\n                // Using JSON to handle newline problems when storing the\n                // key as a secret in Vercel. See:\n                // https://github.com/vercel/vercel/issues/749#issuecomment-707515089\n                privateKey: process.env.FIREBASE_PRIVATE_KEY ? JSON.parse(process.env.FIREBASE_PRIVATE_KEY) : undefined\n            },\n            databaseURL: \"https://hivon-ai.firebaseio.com\"\n        },\n        firebaseClientInitConfig,\n        cookies: {\n            name: \"ExampleApp\",\n            keys: [\n                process.env.COOKIE_SECRET_CURRENT,\n                process.env.COOKIE_SECRET_PREVIOUS\n            ],\n            httpOnly: true,\n            maxAge: TWELVE_DAYS_IN_MS,\n            overwrite: true,\n            path: \"/\",\n            sameSite: \"lax\",\n            secure: \"false # set to true in HTTPS environment\" === \"true\",\n            signed: true\n        }\n    });\n};\n/* harmony default export */ const __WEBPACK_DEFAULT_EXPORT__ = (initAuth);\n//# sourceURL=[module]\n//# sourceMappingURL=data:application/json;charset=utf-8;base64,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c0I7YUFDbkM7WUFDREMsVUFBVTtZQUNWQyxRQUFROUQ7WUFDUitELFdBQVc7WUFDWEMsTUFBTTtZQUNOQyxVQUFVO1lBQ1ZDLFFBQVE5RCwwQ0FBcUMsS0FBSztZQUNsRGdFLFFBQVE7UUFDVjtJQUNGO0FBQ0Y7QUFFQSxpRUFBZW5FLFFBQVFBLEVBQUEiLCJzb3VyY2VzIjpbIndlYnBhY2s6Ly9yZWdpc3RyeS8uL3V0aWxzL2luaXRBdXRoLmpzP2RjYjYiXSwic291cmNlc0NvbnRlbnQiOlsiLyogZ2xvYmFscyB3aW5kb3cgKi9cbmltcG9ydCB7IGluaXRpYWxpemVBcHAgfSBmcm9tICdmaXJlYmFzZS9hcHAnXG5pbXBvcnQgeyBpbml0IH0gZnJvbSAnbmV4dC1maXJlYmFzZS1hdXRoJ1xuaW1wb3J0IGFic29sdXRlVXJsIGZyb20gJ25leHQtYWJzb2x1dGUtdXJsJ1xuXG5jb25zdCBUV0VMVkVfREFZU19JTl9NUyA9IDEyICogNjAgKiA2MCAqIDI0ICogMTAwMFxuXG5jb25zdCBpbml0QXV0aCA9ICgpID0+IHtcbiAgLy8gSW5pdGlhbGl6ZSBGaXJlYmFzZS5cbiAgY29uc3QgZmlyZWJhc2VDbGllbnRJbml0Q29uZmlnID0ge1xuICAgIGFwaUtleTogcHJvY2Vzcy5lbnYuTkVYVF9QVUJMSUNfRklSRUJBU0VfUFVCTElDX0FQSV9LRVksXG4gICAgYXV0aERvbWFpbjogcHJvY2Vzcy5lbnYuTkVYVF9QVUJMSUNfRklSRUJBU0VfQVVUSF9ET01BSU4sXG4gICAgZGF0YWJhc2VVUkw6IHByb2Nlc3MuZW52Lk5FWFRfUFVCTElDX0ZJUkVCQVNFX0RBVEFCQVNFX1VSTCxcbiAgICBwcm9qZWN0SWQ6IHByb2Nlc3MuZW52Lk5FWFRfUFVCTElDX0ZJUkVCQVNFX1BST0pFQ1RfSUQsXG4gICAgc3RvcmFnZUJ1Y2tldDogcHJvY2Vzcy5lbnYuTkVYVF9QVUJMSUNfRklSRUJBU0VfU1RPUkFHRV9CVUNLRVRcbiAgfVxuICBpbml0aWFsaXplQXBwKGZpcmViYXNlQ2xpZW50SW5pdENvbmZpZylcblxuICAvLyBJbml0aWFsaXplIG5leHQtZmlyZWJhc2UtYXV0aC5cbiAgaW5pdCh7XG4gICAgZGVidWc6IHRydWUsXG5cbiAgICAvLyBUaGlzIGRlbW9uc3RyYXRlcyBzZXR0aW5nIGEgZHluYW1pYyBkZXN0aW5hdGlvbiBVUkwgd2hlblxuICAgIC8vIHJlZGlyZWN0aW5nIGZyb20gYXBwIHBhZ2VzLiBBbHRlcm5hdGl2ZWx5LCB5b3UgY2FuIHNpbXBseVxuICAgIC8vIHNwZWNpZnkgYGF1dGhQYWdlVVJMOiAnL2F1dGgtc3NyJ2AuXG4gICAgYXV0aFBhZ2VVUkw6ICh7IGN0eCB9KSA9PiB7XG4gICAgICBjb25zdCBpc1NlcnZlclNpZGUgPSB0eXBlb2Ygd2luZG93ID09PSAndW5kZWZpbmVkJ1xuICAgICAgY29uc3Qgb3JpZ2luID0gaXNTZXJ2ZXJTaWRlXG4gICAgICAgID8gYWJzb2x1dGVVcmwoY3R4LnJlcSkub3JpZ2luXG4gICAgICAgIDogd2luZG93LmxvY2F0aW9uLm9yaWdpblxuICAgICAgY29uc3QgZGVzdFBhdGggPVxuICAgICAgICB0eXBlb2Ygd2luZG93ID09PSAndW5kZWZpbmVkJyA/IGN0eC5yZXNvbHZlZFVybCA6IHdpbmRvdy5sb2NhdGlvbi5ocmVmXG4gICAgICBjb25zdCBkZXN0VVJMID0gbmV3IFVSTChkZXN0UGF0aCwgb3JpZ2luKVxuICAgICAgcmV0dXJuIGAvYXV0aC1zc3I/ZGVzdGluYXRpb249JHtlbmNvZGVVUklDb21wb25lbnQoZGVzdFVSTCl9YFxuICAgIH0sXG5cbiAgICAvLyBUaGlzIGRlbW9uc3RyYXRlcyBzZXR0aW5nIGEgZHluYW1pYyBkZXN0aW5hdGlvbiBVUkwgd2hlblxuICAgIC8vIHJlZGlyZWN0aW5nIGZyb20gYXV0aCBwYWdlcy4gQWx0ZXJuYXRpdmVseSwgeW91IGNhbiBzaW1wbHlcbiAgICAvLyBzcGVjaWZ5IGBhcHBQYWdlVVJMOiAnLydgLlxuICAgIGFwcFBhZ2VVUkw6ICh7IGN0eCB9KSA9PiB7XG4gICAgICBjb25zdCBpc1NlcnZlclNpZGUgPSB0eXBlb2Ygd2luZG93ID09PSAndW5kZWZpbmVkJ1xuICAgICAgY29uc3Qgb3JpZ2luID0gaXNTZXJ2ZXJTaWRlXG4gICAgICAgID8gYWJzb2x1dGVVcmwoY3R4LnJlcSkub3JpZ2luXG4gICAgICAgIDogd2luZG93LmxvY2F0aW9uLm9yaWdpblxuICAgICAgY29uc3QgcGFyYW1zID0gaXNTZXJ2ZXJTaWRlXG4gICAgICAgID8gbmV3IFVSTChjdHgucmVxLnVybCwgb3JpZ2luKS5zZWFyY2hQYXJhbXNcbiAgICAgICAgOiBuZXcgVVJMU2VhcmNoUGFyYW1zKHdpbmRvdy5sb2NhdGlvbi5zZWFyY2gpXG4gICAgICBjb25zdCBkZXN0aW5hdGlvblBhcmFtVmFsID0gcGFyYW1zLmdldCgnZGVzdGluYXRpb24nKVxuICAgICAgICA/IGRlY29kZVVSSUNvbXBvbmVudChwYXJhbXMuZ2V0KCdkZXN0aW5hdGlvbicpKVxuICAgICAgICA6IHVuZGVmaW5lZFxuXG4gICAgICAvLyBCeSBkZWZhdWx0LCBnbyB0byB0aGUgaW5kZXggcGFnZSBpZiB0aGUgZGVzdGluYXRpb24gVVJMXG4gICAgICAvLyBpcyBpbnZhbGlkIG9yIHVuc3BlY2lmaWVkLlxuICAgICAgbGV0IGRlc3RVUkwgPSAnLydcbiAgICAgIGlmIChkZXN0aW5hdGlvblBhcmFtVmFsKSB7XG4gICAgICAgIC8vIFZlcmlmeSB0aGUgcmVkaXJlY3QgVVJMIGhvc3QgaXMgYWxsb3dlZC5cbiAgICAgICAgLy8gaHR0cHM6Ly9vd2FzcC5vcmcvd3d3LXByb2plY3Qtd2ViLXNlY3VyaXR5LXRlc3RpbmctZ3VpZGUvdjQxLzQtV2ViX0FwcGxpY2F0aW9uX1NlY3VyaXR5X1Rlc3RpbmcvMTEtQ2xpZW50X1NpZGVfVGVzdGluZy8wNC1UZXN0aW5nX2Zvcl9DbGllbnRfU2lkZV9VUkxfUmVkaXJlY3RcbiAgICAgICAgY29uc3QgYWxsb3dlZEhvc3RzID0gW1xuICAgICAgICAgICdsb2NhbGhvc3Q6MzAwMCcsXG4gICAgICAgICAgJ25mYS1leGFtcGxlLnZlcmNlbC5hcHAnLFxuICAgICAgICAgICduZmEtZXhhbXBsZS1naXQtdjF4LWdsYWRseS10ZWFtLnZlcmNlbC5hcHAnLFxuICAgICAgICBdXG4gICAgICAgIGNvbnN0IGFsbG93ZWQgPVxuICAgICAgICAgIGFsbG93ZWRIb3N0cy5pbmRleE9mKG5ldyBVUkwoZGVzdGluYXRpb25QYXJhbVZhbCkuaG9zdCkgPiAtMVxuICAgICAgICBpZiAoYWxsb3dlZCkge1xuICAgICAgICAgIGRlc3RVUkwgPSBkZXN0aW5hdGlvblBhcmFtVmFsXG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgLy8gZXNsaW50LWRpc2FibGUtbmV4dC1saW5lIG5vLWNvbnNvbGVcbiAgICAgICAgICBjb25zb2xlLndhcm4oXG4gICAgICAgICAgICBgUmVkaXJlY3QgZGVzdGluYXRpb24gaG9zdCBtdXN0IGJlIG9uZSBvZiAke2FsbG93ZWRIb3N0cy5qb2luKFxuICAgICAgICAgICAgICAnLCAnXG4gICAgICAgICAgICApfS5gXG4gICAgICAgICAgKVxuICAgICAgICB9XG4gICAgICB9XG4gICAgICByZXR1cm4gZGVzdFVSTFxuICAgIH0sXG4gICAgbG9naW5BUElFbmRwb2ludDogJy9hcGkvbG9naW4nLFxuICAgIGxvZ291dEFQSUVuZHBvaW50OiAnL2FwaS9sb2dvdXQnLFxuICAgIGZpcmViYXNlQWRtaW5Jbml0Q29uZmlnOiB7XG4gICAgICBjcmVkZW50aWFsOiB7XG4gICAgICAgIHByb2plY3RJZDogcHJvY2Vzcy5lbnYuTkVYVF9QVUJMSUNfRklSRUJBU0VfUFJPSkVDVF9JRCxcbiAgICAgICAgY2xpZW50RW1haWw6IHByb2Nlc3MuZW52LkZJUkVCQVNFX0NMSUVOVF9FTUFJTCxcbiAgICAgICAgLy8gVXNpbmcgSlNPTiB0byBoYW5kbGUgbmV3bGluZSBwcm9ibGVtcyB3aGVuIHN0b3JpbmcgdGhlXG4gICAgICAgIC8vIGtleSBhcyBhIHNlY3JldCBpbiBWZXJjZWwuIFNlZTpcbiAgICAgICAgLy8gaHR0cHM6Ly9naXRodWIuY29tL3ZlcmNlbC92ZXJjZWwvaXNzdWVzLzc0OSNpc3N1ZWNvbW1lbnQtNzA3NTE1MDg5XG4gICAgICAgIHByaXZhdGVLZXk6IHByb2Nlc3MuZW52LkZJUkVCQVNFX1BSSVZBVEVfS0VZXG4gICAgICAgICAgPyBKU09OLnBhcnNlKHByb2Nlc3MuZW52LkZJUkVCQVNFX1BSSVZBVEVfS0VZKVxuICAgICAgICAgIDogdW5kZWZpbmVkLFxuICAgICAgfSxcbiAgICAgIGRhdGFiYXNlVVJMOiBwcm9jZXNzLmVudi5ORVhUX1BVQkxJQ19GSVJFQkFTRV9EQVRBQkFTRV9VUkwsXG4gICAgfSxcbiAgICBmaXJlYmFzZUNsaWVudEluaXRDb25maWcsXG4gICAgY29va2llczoge1xuICAgICAgbmFtZTogJ0V4YW1wbGVBcHAnLFxuICAgICAga2V5czogW1xuICAgICAgICBwcm9jZXNzLmVudi5DT09LSUVfU0VDUkVUX0NVUlJFTlQsXG4gICAgICAgIHByb2Nlc3MuZW52LkNPT0tJRV9TRUNSRVRfUFJFVklPVVMsXG4gICAgICBdLFxuICAgICAgaHR0cE9ubHk6IHRydWUsXG4gICAgICBtYXhBZ2U6IFRXRUxWRV9EQVlTX0lOX01TLFxuICAgICAgb3ZlcndyaXRlOiB0cnVlLFxuICAgICAgcGF0aDogJy8nLFxuICAgICAgc2FtZVNpdGU6ICdsYXgnLFxuICAgICAgc2VjdXJlOiBwcm9jZXNzLmVudi5ORVhUX1BVQkxJQ19DT09LSUVfU0VDVVJFID09PSAndHJ1ZScsXG4gICAgICBzaWduZWQ6IHRydWUsXG4gICAgfSxcbiAgfSlcbn1cblxuZXhwb3J0IGRlZmF1bHQgaW5pdEF1dGhcbiJdLCJuYW1lcyI6WyJpbml0aWFsaXplQXBwIiwiaW5pdCIsImFic29sdXRlVXJsIiwiVFdFTFZFX0RBWVNfSU5fTVMiLCJpbml0QXV0aCIsImZpcmViYXNlQ2xpZW50SW5pdENvbmZpZyIsImFwaUtleSIsInByb2Nlc3MiLCJlbnYiLCJORVhUX1BVQkxJQ19GSVJFQkFTRV9QVUJMSUNfQVBJX0tFWSIsImF1dGhEb21haW4iLCJORVhUX1BVQkxJQ19GSVJFQkFTRV9BVVRIX0RPTUFJTiIsImRhdGFiYXNlVVJMIiwiTkVYVF9QVUJMSUNfRklSRUJBU0VfREFUQUJBU0VfVVJMIiwicHJvamVjdElkIiwiTkVYVF9QVUJMSUNfRklSRUJBU0VfUFJPSkVDVF9JRCIsInN0b3JhZ2VCdWNrZXQiLCJORVhUX1BVQkxJQ19GSVJFQkFTRV9TVE9SQUdFX0JVQ0tFVCIsImRlYnVnIiwiYXV0aFBhZ2VVUkwiLCJjdHgiLCJpc1NlcnZlclNpZGUiLCJvcmlnaW4iLCJyZXEiLCJ3aW5kb3ciLCJsb2NhdGlvbiIsImRlc3RQYXRoIiwicmVzb2x2ZWRVcmwiLCJocmVmIiwiZGVzdFVSTCIsIlVSTCIsImVuY29kZVVSSUNvbXBvbmVudCIsImFwcFBhZ2VVUkwiLCJwYXJhbXMiLCJ1cmwiLCJzZWFyY2hQYXJhbXMiLCJVUkxTZWFyY2hQYXJhbXMiLCJzZWFyY2giLCJkZXN0aW5hdGlvblBhcmFtVmFsIiwiZ2V0IiwiZGVjb2RlVVJJQ29tcG9uZW50IiwidW5kZWZpbmVkIiwiYWxsb3dlZEhvc3RzIiwiYWxsb3dlZCIsImluZGV4T2YiLCJob3N0IiwiY29uc29sZSIsIndhcm4iLCJqb2luIiwibG9naW5BUElFbmRwb2ludCIsImxvZ291dEFQSUVuZHBvaW50IiwiZmlyZWJhc2VBZG1pbkluaXRDb25maWciLCJjcmVkZW50aWFsIiwiY2xpZW50RW1haWwiLCJGSVJFQkFTRV9DTElFTlRfRU1BSUwiLCJwcml2YXRlS2V5IiwiRklSRUJBU0VfUFJJVkFURV9LRVkiLCJKU09OIiwicGFyc2UiLCJjb29raWVzIiwibmFtZSIsImtleXMiLCJDT09LSUVfU0VDUkVUX0NVUlJFTlQiLCJDT09LSUVfU0VDUkVUX1BSRVZJT1VTIiwiaHR0cE9ubHkiLCJtYXhBZ2UiLCJvdmVyd3JpdGUiLCJwYXRoIiwic2FtZVNpdGUiLCJzZWN1cmUiLCJORVhUX1BVQkxJQ19DT09LSUVfU0VDVVJFIiwic2lnbmVkIl0sInNvdXJjZVJvb3QiOiIifQ==\n//# sourceURL=webpack-internal:///(api)/./utils/initAuth.js\n");

/***/ })

};
;

// load runtime
var __webpack_require__ = require("../../webpack-api-runtime.js");
__webpack_require__.C(exports);
var __webpack_exec__ = (moduleId) => (__webpack_require__(__webpack_require__.s = moduleId))
var __webpack_exports__ = (__webpack_exec__("(api)/./pages/api/login.js"));
module.exports = __webpack_exports__;

})();