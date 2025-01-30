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
exports.id = "pages/api/registry/publish";
exports.ids = ["pages/api/registry/publish"];
exports.modules = {

/***/ "next-firebase-auth":
/*!*************************************!*\
  !*** external "next-firebase-auth" ***!
  \*************************************/
/***/ ((module) => {

module.exports = require("next-firebase-auth");

/***/ }),

/***/ "firebase-admin/firestore":
/*!*******************************************!*\
  !*** external "firebase-admin/firestore" ***!
  \*******************************************/
/***/ ((module) => {

module.exports = import("firebase-admin/firestore");;

/***/ }),

/***/ "(api)/./pages/api/registry/publish.ts":
/*!***************************************!*\
  !*** ./pages/api/registry/publish.ts ***!
  \***************************************/
/***/ ((module, __webpack_exports__, __webpack_require__) => {

eval("__webpack_require__.a(module, async (__webpack_handle_async_dependencies__, __webpack_async_result__) => { try {\n__webpack_require__.r(__webpack_exports__);\n/* harmony export */ __webpack_require__.d(__webpack_exports__, {\n/* harmony export */   \"default\": () => (/* binding */ handler)\n/* harmony export */ });\n/* harmony import */ var next_firebase_auth__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! next-firebase-auth */ \"next-firebase-auth\");\n/* harmony import */ var next_firebase_auth__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(next_firebase_auth__WEBPACK_IMPORTED_MODULE_0__);\n/* harmony import */ var firebase_admin_firestore__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! firebase-admin/firestore */ \"firebase-admin/firestore\");\nvar __webpack_async_dependencies__ = __webpack_handle_async_dependencies__([firebase_admin_firestore__WEBPACK_IMPORTED_MODULE_1__]);\nfirebase_admin_firestore__WEBPACK_IMPORTED_MODULE_1__ = (__webpack_async_dependencies__.then ? (await __webpack_async_dependencies__)() : __webpack_async_dependencies__)[0];\n// pages/api/registry/publish.ts\n\n\nasync function handler(req, res) {\n    if (req.method !== \"POST\") {\n        return res.status(405).json({\n            error: \"Method not allowed\"\n        });\n    }\n    try {\n        // Get the ID token from the Authorization header\n        const token = req.headers.authorization;\n        if (!token) {\n            return res.status(401).json({\n                error: \"No authentication token provided\"\n            });\n        }\n        // Verify the token\n        const user = await (0,next_firebase_auth__WEBPACK_IMPORTED_MODULE_0__.verifyIdToken)(token);\n        if (!user) {\n            return res.status(401).json({\n                error: \"Invalid authentication token\"\n            });\n        }\n        const { fileName, fileSize, downloadURL, uploadedAt } = req.body;\n        // Save to Firestore\n        const db = (0,firebase_admin_firestore__WEBPACK_IMPORTED_MODULE_1__.getFirestore)();\n        await db.collection(\"packages\").add({\n            userId: user.id,\n            userEmail: user.email,\n            fileName,\n            fileSize,\n            downloadURL,\n            uploadedAt,\n            createdAt: new Date().toISOString()\n        });\n        return res.status(200).json({\n            success: true\n        });\n    } catch (error) {\n        console.error(\"Error in publish API:\", error);\n        return res.status(500).json({\n            error: error instanceof Error ? error.message : \"Internal server error\"\n        });\n    }\n}\n\n__webpack_async_result__();\n} catch(e) { __webpack_async_result__(e); } });//# sourceURL=[module]\n//# sourceMappingURL=data:application/json;charset=utf-8;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiKGFwaSkvLi9wYWdlcy9hcGkvcmVnaXN0cnkvcHVibGlzaC50cyIsIm1hcHBpbmdzIjoiOzs7Ozs7Ozs7O0FBQUEsZ0NBQWdDO0FBQ2tCO0FBRUs7QUFFeEMsZUFBZUUsUUFDNUJDLEdBQW1CLEVBQ25CQyxHQUFvQjtJQUVwQixJQUFJRCxJQUFJRSxNQUFNLEtBQUssUUFBUTtRQUN6QixPQUFPRCxJQUFJRSxNQUFNLENBQUMsS0FBS0MsSUFBSSxDQUFDO1lBQUVDLE9BQU87UUFBcUI7SUFDNUQ7SUFFQSxJQUFJO1FBQ0YsaURBQWlEO1FBQ2pELE1BQU1DLFFBQVFOLElBQUlPLE9BQU8sQ0FBQ0MsYUFBYTtRQUV2QyxJQUFJLENBQUNGLE9BQU87WUFDVixPQUFPTCxJQUFJRSxNQUFNLENBQUMsS0FBS0MsSUFBSSxDQUFDO2dCQUFFQyxPQUFPO1lBQW1DO1FBQzFFO1FBRUEsbUJBQW1CO1FBQ25CLE1BQU1JLE9BQU8sTUFBTVosaUVBQWFBLENBQUNTO1FBRWpDLElBQUksQ0FBQ0csTUFBTTtZQUNULE9BQU9SLElBQUlFLE1BQU0sQ0FBQyxLQUFLQyxJQUFJLENBQUM7Z0JBQUVDLE9BQU87WUFBK0I7UUFDdEU7UUFFQSxNQUFNLEVBQUVLLFFBQVEsRUFBRUMsUUFBUSxFQUFFQyxXQUFXLEVBQUVDLFVBQVUsRUFBRSxHQUFHYixJQUFJYyxJQUFJO1FBRWhFLG9CQUFvQjtRQUNwQixNQUFNQyxLQUFLakIsc0VBQVlBO1FBQ3ZCLE1BQU1pQixHQUFHQyxVQUFVLENBQUMsWUFBWUMsR0FBRyxDQUFDO1lBQ2xDQyxRQUFRVCxLQUFLVSxFQUFFO1lBQ2ZDLFdBQVdYLEtBQUtZLEtBQUs7WUFDckJYO1lBQ0FDO1lBQ0FDO1lBQ0FDO1lBQ0FTLFdBQVcsSUFBSUMsT0FBT0MsV0FBVztRQUNuQztRQUVBLE9BQU92QixJQUFJRSxNQUFNLENBQUMsS0FBS0MsSUFBSSxDQUFDO1lBQUVxQixTQUFTO1FBQUs7SUFDOUMsRUFBRSxPQUFPcEIsT0FBTztRQUNkcUIsUUFBUXJCLEtBQUssQ0FBQyx5QkFBeUJBO1FBQ3ZDLE9BQU9KLElBQUlFLE1BQU0sQ0FBQyxLQUFLQyxJQUFJLENBQUM7WUFDMUJDLE9BQU9BLGlCQUFpQnNCLFFBQVF0QixNQUFNdUIsT0FBTyxHQUFHO1FBQ2xEO0lBQ0Y7QUFDRiIsInNvdXJjZXMiOlsid2VicGFjazovL2V4YW1wbGUvLi9wYWdlcy9hcGkvcmVnaXN0cnkvcHVibGlzaC50cz9jNWEyIl0sInNvdXJjZXNDb250ZW50IjpbIi8vIHBhZ2VzL2FwaS9yZWdpc3RyeS9wdWJsaXNoLnRzXG5pbXBvcnQgeyB2ZXJpZnlJZFRva2VuIH0gZnJvbSAnbmV4dC1maXJlYmFzZS1hdXRoJ1xuaW1wb3J0IHR5cGUgeyBOZXh0QXBpUmVxdWVzdCwgTmV4dEFwaVJlc3BvbnNlIH0gZnJvbSAnbmV4dCdcbmltcG9ydCB7IGdldEZpcmVzdG9yZSB9IGZyb20gJ2ZpcmViYXNlLWFkbWluL2ZpcmVzdG9yZSdcblxuZXhwb3J0IGRlZmF1bHQgYXN5bmMgZnVuY3Rpb24gaGFuZGxlcihcbiAgcmVxOiBOZXh0QXBpUmVxdWVzdCxcbiAgcmVzOiBOZXh0QXBpUmVzcG9uc2Vcbikge1xuICBpZiAocmVxLm1ldGhvZCAhPT0gJ1BPU1QnKSB7XG4gICAgcmV0dXJuIHJlcy5zdGF0dXMoNDA1KS5qc29uKHsgZXJyb3I6ICdNZXRob2Qgbm90IGFsbG93ZWQnIH0pXG4gIH1cblxuICB0cnkge1xuICAgIC8vIEdldCB0aGUgSUQgdG9rZW4gZnJvbSB0aGUgQXV0aG9yaXphdGlvbiBoZWFkZXJcbiAgICBjb25zdCB0b2tlbiA9IHJlcS5oZWFkZXJzLmF1dGhvcml6YXRpb25cblxuICAgIGlmICghdG9rZW4pIHtcbiAgICAgIHJldHVybiByZXMuc3RhdHVzKDQwMSkuanNvbih7IGVycm9yOiAnTm8gYXV0aGVudGljYXRpb24gdG9rZW4gcHJvdmlkZWQnIH0pXG4gICAgfVxuXG4gICAgLy8gVmVyaWZ5IHRoZSB0b2tlblxuICAgIGNvbnN0IHVzZXIgPSBhd2FpdCB2ZXJpZnlJZFRva2VuKHRva2VuKVxuICAgIFxuICAgIGlmICghdXNlcikge1xuICAgICAgcmV0dXJuIHJlcy5zdGF0dXMoNDAxKS5qc29uKHsgZXJyb3I6ICdJbnZhbGlkIGF1dGhlbnRpY2F0aW9uIHRva2VuJyB9KVxuICAgIH1cblxuICAgIGNvbnN0IHsgZmlsZU5hbWUsIGZpbGVTaXplLCBkb3dubG9hZFVSTCwgdXBsb2FkZWRBdCB9ID0gcmVxLmJvZHlcblxuICAgIC8vIFNhdmUgdG8gRmlyZXN0b3JlXG4gICAgY29uc3QgZGIgPSBnZXRGaXJlc3RvcmUoKVxuICAgIGF3YWl0IGRiLmNvbGxlY3Rpb24oJ3BhY2thZ2VzJykuYWRkKHtcbiAgICAgIHVzZXJJZDogdXNlci5pZCxcbiAgICAgIHVzZXJFbWFpbDogdXNlci5lbWFpbCxcbiAgICAgIGZpbGVOYW1lLFxuICAgICAgZmlsZVNpemUsXG4gICAgICBkb3dubG9hZFVSTCxcbiAgICAgIHVwbG9hZGVkQXQsXG4gICAgICBjcmVhdGVkQXQ6IG5ldyBEYXRlKCkudG9JU09TdHJpbmcoKSxcbiAgICB9KVxuXG4gICAgcmV0dXJuIHJlcy5zdGF0dXMoMjAwKS5qc29uKHsgc3VjY2VzczogdHJ1ZSB9KVxuICB9IGNhdGNoIChlcnJvcikge1xuICAgIGNvbnNvbGUuZXJyb3IoJ0Vycm9yIGluIHB1Ymxpc2ggQVBJOicsIGVycm9yKVxuICAgIHJldHVybiByZXMuc3RhdHVzKDUwMCkuanNvbih7IFxuICAgICAgZXJyb3I6IGVycm9yIGluc3RhbmNlb2YgRXJyb3IgPyBlcnJvci5tZXNzYWdlIDogJ0ludGVybmFsIHNlcnZlciBlcnJvcicgXG4gICAgfSlcbiAgfVxufSJdLCJuYW1lcyI6WyJ2ZXJpZnlJZFRva2VuIiwiZ2V0RmlyZXN0b3JlIiwiaGFuZGxlciIsInJlcSIsInJlcyIsIm1ldGhvZCIsInN0YXR1cyIsImpzb24iLCJlcnJvciIsInRva2VuIiwiaGVhZGVycyIsImF1dGhvcml6YXRpb24iLCJ1c2VyIiwiZmlsZU5hbWUiLCJmaWxlU2l6ZSIsImRvd25sb2FkVVJMIiwidXBsb2FkZWRBdCIsImJvZHkiLCJkYiIsImNvbGxlY3Rpb24iLCJhZGQiLCJ1c2VySWQiLCJpZCIsInVzZXJFbWFpbCIsImVtYWlsIiwiY3JlYXRlZEF0IiwiRGF0ZSIsInRvSVNPU3RyaW5nIiwic3VjY2VzcyIsImNvbnNvbGUiLCJFcnJvciIsIm1lc3NhZ2UiXSwic291cmNlUm9vdCI6IiJ9\n//# sourceURL=webpack-internal:///(api)/./pages/api/registry/publish.ts\n");

/***/ })

};
;

// load runtime
var __webpack_require__ = require("../../../webpack-api-runtime.js");
__webpack_require__.C(exports);
var __webpack_exec__ = (moduleId) => (__webpack_require__(__webpack_require__.s = moduleId))
var __webpack_exports__ = (__webpack_exec__("(api)/./pages/api/registry/publish.ts"));
module.exports = __webpack_exports__;

})();