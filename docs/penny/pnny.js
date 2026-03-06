(function() {
    const t = document.createElement("link").relList;
    if (t && t.supports && t.supports("modulepreload"))
        return;
    for (const l of document.querySelectorAll('link[rel="modulepreload"]'))
        r(l);
    new MutationObserver(l => {
        for (const o of l)
            if (o.type === "childList")
                for (const i of o.addedNodes)
                    i.tagName === "LINK" && i.rel === "modulepreload" && r(i)
    }
    ).observe(document, {
        childList: !0,
        subtree: !0
    });
    function n(l) {
        const o = {};
        return l.integrity && (o.integrity = l.integrity),
        l.referrerPolicy && (o.referrerPolicy = l.referrerPolicy),
        l.crossOrigin === "use-credentials" ? o.credentials = "include" : l.crossOrigin === "anonymous" ? o.credentials = "omit" : o.credentials = "same-origin",
        o
    }
    function r(l) {
        if (l.ep)
            return;
        l.ep = !0;
        const o = n(l);
        fetch(l.href, o)
    }
}
)();
function yf(e) {
    return e && e.__esModule && Object.prototype.hasOwnProperty.call(e, "default") ? e.default : e
}
var za = {
    exports: {}
}
  , ql = {}
  , _a = {
    exports: {}
}
  , H = {};
/**
 * @license React
 * react.production.min.js
 *
 * Copyright (c) Facebook, Inc. and its affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */
var Dr = Symbol.for("react.element")
  , gf = Symbol.for("react.portal")
  , vf = Symbol.for("react.fragment")
  , xf = Symbol.for("react.strict_mode")
  , Sf = Symbol.for("react.profiler")
  , kf = Symbol.for("react.provider")
  , wf = Symbol.for("react.context")
  , Cf = Symbol.for("react.forward_ref")
  , jf = Symbol.for("react.suspense")
  , Ef = Symbol.for("react.memo")
  , zf = Symbol.for("react.lazy")
  , mu = Symbol.iterator;
function _f(e) {
    return e === null || typeof e != "object" ? null : (e = mu && e[mu] || e["@@iterator"],
    typeof e == "function" ? e : null)
}
var La = {
    isMounted: function() {
        return !1
    },
    enqueueForceUpdate: function() {},
    enqueueReplaceState: function() {},
    enqueueSetState: function() {}
}
  , Ta = Object.assign
  , Pa = {};
function Qn(e, t, n) {
    this.props = e,
    this.context = t,
    this.refs = Pa,
    this.updater = n || La
}
Qn.prototype.isReactComponent = {};
Qn.prototype.setState = function(e, t) {
    if (typeof e != "object" && typeof e != "function" && e != null)
        throw Error("setState(...): takes an object of state variables to update or a function which returns an object of state variables.");
    this.updater.enqueueSetState(this, e, t, "setState")
}
;
Qn.prototype.forceUpdate = function(e) {
    this.updater.enqueueForceUpdate(this, e, "forceUpdate")
}
;
function Na() {}
Na.prototype = Qn.prototype;
function qi(e, t, n) {
    this.props = e,
    this.context = t,
    this.refs = Pa,
    this.updater = n || La
}
var bi = qi.prototype = new Na;
bi.constructor = qi;
Ta(bi, Qn.prototype);
bi.isPureReactComponent = !0;
var yu = Array.isArray
  , Fa = Object.prototype.hasOwnProperty
  , es = {
    current: null
}
  , Ia = {
    key: !0,
    ref: !0,
    __self: !0,
    __source: !0
};
function Ra(e, t, n) {
    var r, l = {}, o = null, i = null;
    if (t != null)
        for (r in t.ref !== void 0 && (i = t.ref),
        t.key !== void 0 && (o = "" + t.key),
        t)
            Fa.call(t, r) && !Ia.hasOwnProperty(r) && (l[r] = t[r]);
    var u = arguments.length - 2;
    if (u === 1)
        l.children = n;
    else if (1 < u) {
        for (var c = Array(u), f = 0; f < u; f++)
            c[f] = arguments[f + 2];
        l.children = c
    }
    if (e && e.defaultProps)
        for (r in u = e.defaultProps,
        u)
            l[r] === void 0 && (l[r] = u[r]);
    return {
        $$typeof: Dr,
        type: e,
        key: o,
        ref: i,
        props: l,
        _owner: es.current
    }
}
function Lf(e, t) {
    return {
        $$typeof: Dr,
        type: e.type,
        key: t,
        ref: e.ref,
        props: e.props,
        _owner: e._owner
    }
}
function ts(e) {
    return typeof e == "object" && e !== null && e.$$typeof === Dr
}
function Tf(e) {
    var t = {
        "=": "=0",
        ":": "=2"
    };
    return "$" + e.replace(/[=:]/g, function(n) {
        return t[n]
    })
}
var gu = /\/+/g;
function Lo(e, t) {
    return typeof e == "object" && e !== null && e.key != null ? Tf("" + e.key) : t.toString(36)
}
function yl(e, t, n, r, l) {
    var o = typeof e;
    (o === "undefined" || o === "boolean") && (e = null);
    var i = !1;
    if (e === null)
        i = !0;
    else
        switch (o) {
        case "string":
        case "number":
            i = !0;
            break;
        case "object":
            switch (e.$$typeof) {
            case Dr:
            case gf:
                i = !0
            }
        }
    if (i)
        return i = e,
        l = l(i),
        e = r === "" ? "." + Lo(i, 0) : r,
        yu(l) ? (n = "",
        e != null && (n = e.replace(gu, "$&/") + "/"),
        yl(l, t, n, "", function(f) {
            return f
        })) : l != null && (ts(l) && (l = Lf(l, n + (!l.key || i && i.key === l.key ? "" : ("" + l.key).replace(gu, "$&/") + "/") + e)),
        t.push(l)),
        1;
    if (i = 0,
    r = r === "" ? "." : r + ":",
    yu(e))
        for (var u = 0; u < e.length; u++) {
            o = e[u];
            var c = r + Lo(o, u);
            i += yl(o, t, n, c, l)
        }
    else if (c = _f(e),
    typeof c == "function")
        for (e = c.call(e),
        u = 0; !(o = e.next()).done; )
            o = o.value,
            c = r + Lo(o, u++),
            i += yl(o, t, n, c, l);
    else if (o === "object")
        throw t = String(e),
        Error("Objects are not valid as a React child (found: " + (t === "[object Object]" ? "object with keys {" + Object.keys(e).join(", ") + "}" : t) + "). If you meant to render a collection of children, use an array instead.");
    return i
}
function Zr(e, t, n) {
    if (e == null)
        return e;
    var r = []
      , l = 0;
    return yl(e, r, "", "", function(o) {
        return t.call(n, o, l++)
    }),
    r
}
function Pf(e) {
    if (e._status === -1) {
        var t = e._result;
        t = t(),
        t.then(function(n) {
            (e._status === 0 || e._status === -1) && (e._status = 1,
            e._result = n)
        }, function(n) {
            (e._status === 0 || e._status === -1) && (e._status = 2,
            e._result = n)
        }),
        e._status === -1 && (e._status = 0,
        e._result = t)
    }
    if (e._status === 1)
        return e._result.default;
    throw e._result
}
var Le = {
    current: null
}
  , gl = {
    transition: null
}
  , Nf = {
    ReactCurrentDispatcher: Le,
    ReactCurrentBatchConfig: gl,
    ReactCurrentOwner: es
};
function Da() {
    throw Error("act(...) is not supported in production builds of React.")
}
H.Children = {
    map: Zr,
    forEach: function(e, t, n) {
        Zr(e, function() {
            t.apply(this, arguments)
        }, n)
    },
    count: function(e) {
        var t = 0;
        return Zr(e, function() {
            t++
        }),
        t
    },
    toArray: function(e) {
        return Zr(e, function(t) {
            return t
        }) || []
    },
    only: function(e) {
        if (!ts(e))
            throw Error("React.Children.only expected to receive a single React element child.");
        return e
    }
};
H.Component = Qn;
H.Fragment = vf;
H.Profiler = Sf;
H.PureComponent = qi;
H.StrictMode = xf;
H.Suspense = jf;
H.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED = Nf;
H.act = Da;
H.cloneElement = function(e, t, n) {
    if (e == null)
        throw Error("React.cloneElement(...): The argument must be a React element, but you passed " + e + ".");
    var r = Ta({}, e.props)
      , l = e.key
      , o = e.ref
      , i = e._owner;
    if (t != null) {
        if (t.ref !== void 0 && (o = t.ref,
        i = es.current),
        t.key !== void 0 && (l = "" + t.key),
        e.type && e.type.defaultProps)
            var u = e.type.defaultProps;
        for (c in t)
            Fa.call(t, c) && !Ia.hasOwnProperty(c) && (r[c] = t[c] === void 0 && u !== void 0 ? u[c] : t[c])
    }
    var c = arguments.length - 2;
    if (c === 1)
        r.children = n;
    else if (1 < c) {
        u = Array(c);
        for (var f = 0; f < c; f++)
            u[f] = arguments[f + 2];
        r.children = u
    }
    return {
        $$typeof: Dr,
        type: e.type,
        key: l,
        ref: o,
        props: r,
        _owner: i
    }
}
;
H.createContext = function(e) {
    return e = {
        $$typeof: wf,
        _currentValue: e,
        _currentValue2: e,
        _threadCount: 0,
        Provider: null,
        Consumer: null,
        _defaultValue: null,
        _globalName: null
    },
    e.Provider = {
        $$typeof: kf,
        _context: e
    },
    e.Consumer = e
}
;
H.createElement = Ra;
H.createFactory = function(e) {
    var t = Ra.bind(null, e);
    return t.type = e,
    t
}
;
H.createRef = function() {
    return {
        current: null
    }
}
;
H.forwardRef = function(e) {
    return {
        $$typeof: Cf,
        render: e
    }
}
;
H.isValidElement = ts;
H.lazy = function(e) {
    return {
        $$typeof: zf,
        _payload: {
            _status: -1,
            _result: e
        },
        _init: Pf
    }
}
;
H.memo = function(e, t) {
    return {
        $$typeof: Ef,
        type: e,
        compare: t === void 0 ? null : t
    }
}
;
H.startTransition = function(e) {
    var t = gl.transition;
    gl.transition = {};
    try {
        e()
    } finally {
        gl.transition = t
    }
}
;
H.unstable_act = Da;
H.useCallback = function(e, t) {
    return Le.current.useCallback(e, t)
}
;
H.useContext = function(e) {
    return Le.current.useContext(e)
}
;
H.useDebugValue = function() {}
;
H.useDeferredValue = function(e) {
    return Le.current.useDeferredValue(e)
}
;
H.useEffect = function(e, t) {
    return Le.current.useEffect(e, t)
}
;
H.useId = function() {
    return Le.current.useId()
}
;
H.useImperativeHandle = function(e, t, n) {
    return Le.current.useImperativeHandle(e, t, n)
}
;
H.useInsertionEffect = function(e, t) {
    return Le.current.useInsertionEffect(e, t)
}
;
H.useLayoutEffect = function(e, t) {
    return Le.current.useLayoutEffect(e, t)
}
;
H.useMemo = function(e, t) {
    return Le.current.useMemo(e, t)
}
;
H.useReducer = function(e, t, n) {
    return Le.current.useReducer(e, t, n)
}
;
H.useRef = function(e) {
    return Le.current.useRef(e)
}
;
H.useState = function(e) {
    return Le.current.useState(e)
}
;
H.useSyncExternalStore = function(e, t, n) {
    return Le.current.useSyncExternalStore(e, t, n)
}
;
H.useTransition = function() {
    return Le.current.useTransition()
}
;
H.version = "18.3.1";
_a.exports = H;
var T = _a.exports;
const Ff = yf(T);
/**
 * @license React
 * react-jsx-runtime.production.min.js
 *
 * Copyright (c) Facebook, Inc. and its affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */
var If = T
  , Rf = Symbol.for("react.element")
  , Df = Symbol.for("react.fragment")
  , Of = Object.prototype.hasOwnProperty
  , Mf = If.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED.ReactCurrentOwner
  , Af = {
    key: !0,
    ref: !0,
    __self: !0,
    __source: !0
};
function Oa(e, t, n) {
    var r, l = {}, o = null, i = null;
    n !== void 0 && (o = "" + n),
    t.key !== void 0 && (o = "" + t.key),
    t.ref !== void 0 && (i = t.ref);
    for (r in t)
        Of.call(t, r) && !Af.hasOwnProperty(r) && (l[r] = t[r]);
    if (e && e.defaultProps)
        for (r in t = e.defaultProps,
        t)
            l[r] === void 0 && (l[r] = t[r]);
    return {
        $$typeof: Rf,
        type: e,
        key: o,
        ref: i,
        props: l,
        _owner: Mf.current
    }
}
ql.Fragment = Df;
ql.jsx = Oa;
ql.jsxs = Oa;
za.exports = ql;
var s = za.exports
  , oi = {}
  , Ma = {
    exports: {}
}
  , $e = {}
  , Aa = {
    exports: {}
}
  , Wa = {};
/**
 * @license React
 * scheduler.production.min.js
 *
 * Copyright (c) Facebook, Inc. and its affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */
(function(e) {
    function t(L, A) {
        var W = L.length;
        L.push(A);
        e: for (; 0 < W; ) {
            var ne = W - 1 >>> 1
              , U = L[ne];
            if (0 < l(U, A))
                L[ne] = A,
                L[W] = U,
                W = ne;
            else
                break e
        }
    }
    function n(L) {
        return L.length === 0 ? null : L[0]
    }
    function r(L) {
        if (L.length === 0)
            return null;
        var A = L[0]
          , W = L.pop();
        if (W !== A) {
            L[0] = W;
            e: for (var ne = 0, U = L.length, dt = U >>> 1; ne < dt; ) {
                var je = 2 * (ne + 1) - 1
                  , Ee = L[je]
                  , xe = je + 1
                  , He = L[xe];
                if (0 > l(Ee, W))
                    xe < U && 0 > l(He, Ee) ? (L[ne] = He,
                    L[xe] = W,
                    ne = xe) : (L[ne] = Ee,
                    L[je] = W,
                    ne = je);
                else if (xe < U && 0 > l(He, W))
                    L[ne] = He,
                    L[xe] = W,
                    ne = xe;
                else
                    break e
            }
        }
        return A
    }
    function l(L, A) {
        var W = L.sortIndex - A.sortIndex;
        return W !== 0 ? W : L.id - A.id
    }
    if (typeof performance == "object" && typeof performance.now == "function") {
        var o = performance;
        e.unstable_now = function() {
            return o.now()
        }
    } else {
        var i = Date
          , u = i.now();
        e.unstable_now = function() {
            return i.now() - u
        }
    }
    var c = []
      , f = []
      , v = 1
      , g = null
      , y = 3
      , C = !1
      , j = !1
      , _ = !1
      , Z = typeof setTimeout == "function" ? setTimeout : null
      , p = typeof clearTimeout == "function" ? clearTimeout : null
      , d = typeof setImmediate < "u" ? setImmediate : null;
    typeof navigator < "u" && navigator.scheduling !== void 0 && navigator.scheduling.isInputPending !== void 0 && navigator.scheduling.isInputPending.bind(navigator.scheduling);
    function m(L) {
        for (var A = n(f); A !== null; ) {
            if (A.callback === null)
                r(f);
            else if (A.startTime <= L)
                r(f),
                A.sortIndex = A.expirationTime,
                t(c, A);
            else
                break;
            A = n(f)
        }
    }
    function S(L) {
        if (_ = !1,
        m(L),
        !j)
            if (n(c) !== null)
                j = !0,
                dn(E);
            else {
                var A = n(f);
                A !== null && rt(S, A.startTime - L)
            }
    }
    function E(L, A) {
        j = !1,
        _ && (_ = !1,
        p(R),
        R = -1),
        C = !0;
        var W = y;
        try {
            for (m(A),
            g = n(c); g !== null && (!(g.expirationTime > A) || L && !Pe()); ) {
                var ne = g.callback;
                if (typeof ne == "function") {
                    g.callback = null,
                    y = g.priorityLevel;
                    var U = ne(g.expirationTime <= A);
                    A = e.unstable_now(),
                    typeof U == "function" ? g.callback = U : g === n(c) && r(c),
                    m(A)
                } else
                    r(c);
                g = n(c)
            }
            if (g !== null)
                var dt = !0;
            else {
                var je = n(f);
                je !== null && rt(S, je.startTime - A),
                dt = !1
            }
            return dt
        } finally {
            g = null,
            y = W,
            C = !1
        }
    }
    var I = !1
      , F = null
      , R = -1
      , te = 5
      , $ = -1;
    function Pe() {
        return !(e.unstable_now() - $ < te)
    }
    function Ct() {
        if (F !== null) {
            var L = e.unstable_now();
            $ = L;
            var A = !0;
            try {
                A = F(!0, L)
            } finally {
                A ? jt() : (I = !1,
                F = null)
            }
        } else
            I = !1
    }
    var jt;
    if (typeof d == "function")
        jt = function() {
            d(Ct)
        }
        ;
    else if (typeof MessageChannel < "u") {
        var Xn = new MessageChannel
          , Br = Xn.port2;
        Xn.port1.onmessage = Ct,
        jt = function() {
            Br.postMessage(null)
        }
    } else
        jt = function() {
            Z(Ct, 0)
        }
        ;
    function dn(L) {
        F = L,
        I || (I = !0,
        jt())
    }
    function rt(L, A) {
        R = Z(function() {
            L(e.unstable_now())
        }, A)
    }
    e.unstable_IdlePriority = 5,
    e.unstable_ImmediatePriority = 1,
    e.unstable_LowPriority = 4,
    e.unstable_NormalPriority = 3,
    e.unstable_Profiling = null,
    e.unstable_UserBlockingPriority = 2,
    e.unstable_cancelCallback = function(L) {
        L.callback = null
    }
    ,
    e.unstable_continueExecution = function() {
        j || C || (j = !0,
        dn(E))
    }
    ,
    e.unstable_forceFrameRate = function(L) {
        0 > L || 125 < L ? console.error("forceFrameRate takes a positive int between 0 and 125, forcing frame rates higher than 125 fps is not supported") : te = 0 < L ? Math.floor(1e3 / L) : 5
    }
    ,
    e.unstable_getCurrentPriorityLevel = function() {
        return y
    }
    ,
    e.unstable_getFirstCallbackNode = function() {
        return n(c)
    }
    ,
    e.unstable_next = function(L) {
        switch (y) {
        case 1:
        case 2:
        case 3:
            var A = 3;
            break;
        default:
            A = y
        }
        var W = y;
        y = A;
        try {
            return L()
        } finally {
            y = W
        }
    }
    ,
    e.unstable_pauseExecution = function() {}
    ,
    e.unstable_requestPaint = function() {}
    ,
    e.unstable_runWithPriority = function(L, A) {
        switch (L) {
        case 1:
        case 2:
        case 3:
        case 4:
        case 5:
            break;
        default:
            L = 3
        }
        var W = y;
        y = L;
        try {
            return A()
        } finally {
            y = W
        }
    }
    ,
    e.unstable_scheduleCallback = function(L, A, W) {
        var ne = e.unstable_now();
        switch (typeof W == "object" && W !== null ? (W = W.delay,
        W = typeof W == "number" && 0 < W ? ne + W : ne) : W = ne,
        L) {
        case 1:
            var U = -1;
            break;
        case 2:
            U = 250;
            break;
        case 5:
            U = 1073741823;
            break;
        case 4:
            U = 1e4;
            break;
        default:
            U = 5e3
        }
        return U = W + U,
        L = {
            id: v++,
            callback: A,
            priorityLevel: L,
            startTime: W,
            expirationTime: U,
            sortIndex: -1
        },
        W > ne ? (L.sortIndex = W,
        t(f, L),
        n(c) === null && L === n(f) && (_ ? (p(R),
        R = -1) : _ = !0,
        rt(S, W - ne))) : (L.sortIndex = U,
        t(c, L),
        j || C || (j = !0,
        dn(E))),
        L
    }
    ,
    e.unstable_shouldYield = Pe,
    e.unstable_wrapCallback = function(L) {
        var A = y;
        return function() {
            var W = y;
            y = A;
            try {
                return L.apply(this, arguments)
            } finally {
                y = W
            }
        }
    }
}
)(Wa);
Aa.exports = Wa;
var Wf = Aa.exports;
/**
 * @license React
 * react-dom.production.min.js
 *
 * Copyright (c) Facebook, Inc. and its affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */
var Bf = T
  , Be = Wf;
function w(e) {
    for (var t = "https://reactjs.org/docs/error-decoder.html?invariant=" + e, n = 1; n < arguments.length; n++)
        t += "&args[]=" + encodeURIComponent(arguments[n]);
    return "Minified React error #" + e + "; visit " + t + " for the full message or use the non-minified dev environment for full errors and additional helpful warnings."
}
var Ba = new Set
  , vr = {};
function an(e, t) {
    An(e, t),
    An(e + "Capture", t)
}
function An(e, t) {
    for (vr[e] = t,
    e = 0; e < t.length; e++)
        Ba.add(t[e])
}
var vt = !(typeof window > "u" || typeof window.document > "u" || typeof window.document.createElement > "u")
  , ii = Object.prototype.hasOwnProperty
  , $f = /^[:A-Z_a-z\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u02FF\u0370-\u037D\u037F-\u1FFF\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD][:A-Z_a-z\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u02FF\u0370-\u037D\u037F-\u1FFF\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD\-.0-9\u00B7\u0300-\u036F\u203F-\u2040]*$/
  , vu = {}
  , xu = {};
function Uf(e) {
    return ii.call(xu, e) ? !0 : ii.call(vu, e) ? !1 : $f.test(e) ? xu[e] = !0 : (vu[e] = !0,
    !1)
}
function Hf(e, t, n, r) {
    if (n !== null && n.type === 0)
        return !1;
    switch (typeof t) {
    case "function":
    case "symbol":
        return !0;
    case "boolean":
        return r ? !1 : n !== null ? !n.acceptsBooleans : (e = e.toLowerCase().slice(0, 5),
        e !== "data-" && e !== "aria-");
    default:
        return !1
    }
}
function Vf(e, t, n, r) {
    if (t === null || typeof t > "u" || Hf(e, t, n, r))
        return !0;
    if (r)
        return !1;
    if (n !== null)
        switch (n.type) {
        case 3:
            return !t;
        case 4:
            return t === !1;
        case 5:
            return isNaN(t);
        case 6:
            return isNaN(t) || 1 > t
        }
    return !1
}
function Te(e, t, n, r, l, o, i) {
    this.acceptsBooleans = t === 2 || t === 3 || t === 4,
    this.attributeName = r,
    this.attributeNamespace = l,
    this.mustUseProperty = n,
    this.propertyName = e,
    this.type = t,
    this.sanitizeURL = o,
    this.removeEmptyString = i
}
var ve = {};
"children dangerouslySetInnerHTML defaultValue defaultChecked innerHTML suppressContentEditableWarning suppressHydrationWarning style".split(" ").forEach(function(e) {
    ve[e] = new Te(e,0,!1,e,null,!1,!1)
});
[["acceptCharset", "accept-charset"], ["className", "class"], ["htmlFor", "for"], ["httpEquiv", "http-equiv"]].forEach(function(e) {
    var t = e[0];
    ve[t] = new Te(t,1,!1,e[1],null,!1,!1)
});
["contentEditable", "draggable", "spellCheck", "value"].forEach(function(e) {
    ve[e] = new Te(e,2,!1,e.toLowerCase(),null,!1,!1)
});
["autoReverse", "externalResourcesRequired", "focusable", "preserveAlpha"].forEach(function(e) {
    ve[e] = new Te(e,2,!1,e,null,!1,!1)
});
"allowFullScreen async autoFocus autoPlay controls default defer disabled disablePictureInPicture disableRemotePlayback formNoValidate hidden loop noModule noValidate open playsInline readOnly required reversed scoped seamless itemScope".split(" ").forEach(function(e) {
    ve[e] = new Te(e,3,!1,e.toLowerCase(),null,!1,!1)
});
["checked", "multiple", "muted", "selected"].forEach(function(e) {
    ve[e] = new Te(e,3,!0,e,null,!1,!1)
});
["capture", "download"].forEach(function(e) {
    ve[e] = new Te(e,4,!1,e,null,!1,!1)
});
["cols", "rows", "size", "span"].forEach(function(e) {
    ve[e] = new Te(e,6,!1,e,null,!1,!1)
});
["rowSpan", "start"].forEach(function(e) {
    ve[e] = new Te(e,5,!1,e.toLowerCase(),null,!1,!1)
});
var ns = /[\-:]([a-z])/g;
function rs(e) {
    return e[1].toUpperCase()
}
"accent-height alignment-baseline arabic-form baseline-shift cap-height clip-path clip-rule color-interpolation color-interpolation-filters color-profile color-rendering dominant-baseline enable-background fill-opacity fill-rule flood-color flood-opacity font-family font-size font-size-adjust font-stretch font-style font-variant font-weight glyph-name glyph-orientation-horizontal glyph-orientation-vertical horiz-adv-x horiz-origin-x image-rendering letter-spacing lighting-color marker-end marker-mid marker-start overline-position overline-thickness paint-order panose-1 pointer-events rendering-intent shape-rendering stop-color stop-opacity strikethrough-position strikethrough-thickness stroke-dasharray stroke-dashoffset stroke-linecap stroke-linejoin stroke-miterlimit stroke-opacity stroke-width text-anchor text-decoration text-rendering underline-position underline-thickness unicode-bidi unicode-range units-per-em v-alphabetic v-hanging v-ideographic v-mathematical vector-effect vert-adv-y vert-origin-x vert-origin-y word-spacing writing-mode xmlns:xlink x-height".split(" ").forEach(function(e) {
    var t = e.replace(ns, rs);
    ve[t] = new Te(t,1,!1,e,null,!1,!1)
});
"xlink:actuate xlink:arcrole xlink:role xlink:show xlink:title xlink:type".split(" ").forEach(function(e) {
    var t = e.replace(ns, rs);
    ve[t] = new Te(t,1,!1,e,"http://www.w3.org/1999/xlink",!1,!1)
});
["xml:base", "xml:lang", "xml:space"].forEach(function(e) {
    var t = e.replace(ns, rs);
    ve[t] = new Te(t,1,!1,e,"http://www.w3.org/XML/1998/namespace",!1,!1)
});
["tabIndex", "crossOrigin"].forEach(function(e) {
    ve[e] = new Te(e,1,!1,e.toLowerCase(),null,!1,!1)
});
ve.xlinkHref = new Te("xlinkHref",1,!1,"xlink:href","http://www.w3.org/1999/xlink",!0,!1);
["src", "href", "action", "formAction"].forEach(function(e) {
    ve[e] = new Te(e,1,!1,e.toLowerCase(),null,!0,!0)
});
function ls(e, t, n, r) {
    var l = ve.hasOwnProperty(t) ? ve[t] : null;
    (l !== null ? l.type !== 0 : r || !(2 < t.length) || t[0] !== "o" && t[0] !== "O" || t[1] !== "n" && t[1] !== "N") && (Vf(t, n, l, r) && (n = null),
    r || l === null ? Uf(t) && (n === null ? e.removeAttribute(t) : e.setAttribute(t, "" + n)) : l.mustUseProperty ? e[l.propertyName] = n === null ? l.type === 3 ? !1 : "" : n : (t = l.attributeName,
    r = l.attributeNamespace,
    n === null ? e.removeAttribute(t) : (l = l.type,
    n = l === 3 || l === 4 && n === !0 ? "" : "" + n,
    r ? e.setAttributeNS(r, t, n) : e.setAttribute(t, n))))
}
var wt = Bf.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED
  , qr = Symbol.for("react.element")
  , Sn = Symbol.for("react.portal")
  , kn = Symbol.for("react.fragment")
  , os = Symbol.for("react.strict_mode")
  , si = Symbol.for("react.profiler")
  , $a = Symbol.for("react.provider")
  , Ua = Symbol.for("react.context")
  , is = Symbol.for("react.forward_ref")
  , ui = Symbol.for("react.suspense")
  , ai = Symbol.for("react.suspense_list")
  , ss = Symbol.for("react.memo")
  , _t = Symbol.for("react.lazy")
  , Ha = Symbol.for("react.offscreen")
  , Su = Symbol.iterator;
function Jn(e) {
    return e === null || typeof e != "object" ? null : (e = Su && e[Su] || e["@@iterator"],
    typeof e == "function" ? e : null)
}
var se = Object.assign, To;
function or(e) {
    if (To === void 0)
        try {
            throw Error()
        } catch (n) {
            var t = n.stack.trim().match(/\n( *(at )?)/);
            To = t && t[1] || ""
        }
    return `
` + To + e
}
var Po = !1;
function No(e, t) {
    if (!e || Po)
        return "";
    Po = !0;
    var n = Error.prepareStackTrace;
    Error.prepareStackTrace = void 0;
    try {
        if (t)
            if (t = function() {
                throw Error()
            }
            ,
            Object.defineProperty(t.prototype, "props", {
                set: function() {
                    throw Error()
                }
            }),
            typeof Reflect == "object" && Reflect.construct) {
                try {
                    Reflect.construct(t, [])
                } catch (f) {
                    var r = f
                }
                Reflect.construct(e, [], t)
            } else {
                try {
                    t.call()
                } catch (f) {
                    r = f
                }
                e.call(t.prototype)
            }
        else {
            try {
                throw Error()
            } catch (f) {
                r = f
            }
            e()
        }
    } catch (f) {
        if (f && r && typeof f.stack == "string") {
            for (var l = f.stack.split(`
`), o = r.stack.split(`
`), i = l.length - 1, u = o.length - 1; 1 <= i && 0 <= u && l[i] !== o[u]; )
                u--;
            for (; 1 <= i && 0 <= u; i--,
            u--)
                if (l[i] !== o[u]) {
                    if (i !== 1 || u !== 1)
                        do
                            if (i--,
                            u--,
                            0 > u || l[i] !== o[u]) {
                                var c = `
` + l[i].replace(" at new ", " at ");
                                return e.displayName && c.includes("<anonymous>") && (c = c.replace("<anonymous>", e.displayName)),
                                c
                            }
                        while (1 <= i && 0 <= u);
                    break
                }
        }
    } finally {
        Po = !1,
        Error.prepareStackTrace = n
    }
    return (e = e ? e.displayName || e.name : "") ? or(e) : ""
}
function Qf(e) {
    switch (e.tag) {
    case 5:
        return or(e.type);
    case 16:
        return or("Lazy");
    case 13:
        return or("Suspense");
    case 19:
        return or("SuspenseList");
    case 0:
    case 2:
    case 15:
        return e = No(e.type, !1),
        e;
    case 11:
        return e = No(e.type.render, !1),
        e;
    case 1:
        return e = No(e.type, !0),
        e;
    default:
        return ""
    }
}
function ci(e) {
    if (e == null)
        return null;
    if (typeof e == "function")
        return e.displayName || e.name || null;
    if (typeof e == "string")
        return e;
    switch (e) {
    case kn:
        return "Fragment";
    case Sn:
        return "Portal";
    case si:
        return "Profiler";
    case os:
        return "StrictMode";
    case ui:
        return "Suspense";
    case ai:
        return "SuspenseList"
    }
    if (typeof e == "object")
        switch (e.$$typeof) {
        case Ua:
            return (e.displayName || "Context") + ".Consumer";
        case $a:
            return (e._context.displayName || "Context") + ".Provider";
        case is:
            var t = e.render;
            return e = e.displayName,
            e || (e = t.displayName || t.name || "",
            e = e !== "" ? "ForwardRef(" + e + ")" : "ForwardRef"),
            e;
        case ss:
            return t = e.displayName || null,
            t !== null ? t : ci(e.type) || "Memo";
        case _t:
            t = e._payload,
            e = e._init;
            try {
                return ci(e(t))
            } catch {}
        }
    return null
}
function Kf(e) {
    var t = e.type;
    switch (e.tag) {
    case 24:
        return "Cache";
    case 9:
        return (t.displayName || "Context") + ".Consumer";
    case 10:
        return (t._context.displayName || "Context") + ".Provider";
    case 18:
        return "DehydratedFragment";
    case 11:
        return e = t.render,
        e = e.displayName || e.name || "",
        t.displayName || (e !== "" ? "ForwardRef(" + e + ")" : "ForwardRef");
    case 7:
        return "Fragment";
    case 5:
        return t;
    case 4:
        return "Portal";
    case 3:
        return "Root";
    case 6:
        return "Text";
    case 16:
        return ci(t);
    case 8:
        return t === os ? "StrictMode" : "Mode";
    case 22:
        return "Offscreen";
    case 12:
        return "Profiler";
    case 21:
        return "Scope";
    case 13:
        return "Suspense";
    case 19:
        return "SuspenseList";
    case 25:
        return "TracingMarker";
    case 1:
    case 0:
    case 17:
    case 2:
    case 14:
    case 15:
        if (typeof t == "function")
            return t.displayName || t.name || null;
        if (typeof t == "string")
            return t
    }
    return null
}
function $t(e) {
    switch (typeof e) {
    case "boolean":
    case "number":
    case "string":
    case "undefined":
        return e;
    case "object":
        return e;
    default:
        return ""
    }
}
function Va(e) {
    var t = e.type;
    return (e = e.nodeName) && e.toLowerCase() === "input" && (t === "checkbox" || t === "radio")
}
function Yf(e) {
    var t = Va(e) ? "checked" : "value"
      , n = Object.getOwnPropertyDescriptor(e.constructor.prototype, t)
      , r = "" + e[t];
    if (!e.hasOwnProperty(t) && typeof n < "u" && typeof n.get == "function" && typeof n.set == "function") {
        var l = n.get
          , o = n.set;
        return Object.defineProperty(e, t, {
            configurable: !0,
            get: function() {
                return l.call(this)
            },
            set: function(i) {
                r = "" + i,
                o.call(this, i)
            }
        }),
        Object.defineProperty(e, t, {
            enumerable: n.enumerable
        }),
        {
            getValue: function() {
                return r
            },
            setValue: function(i) {
                r = "" + i
            },
            stopTracking: function() {
                e._valueTracker = null,
                delete e[t]
            }
        }
    }
}
function br(e) {
    e._valueTracker || (e._valueTracker = Yf(e))
}
function Qa(e) {
    if (!e)
        return !1;
    var t = e._valueTracker;
    if (!t)
        return !0;
    var n = t.getValue()
      , r = "";
    return e && (r = Va(e) ? e.checked ? "true" : "false" : e.value),
    e = r,
    e !== n ? (t.setValue(e),
    !0) : !1
}
function Ll(e) {
    if (e = e || (typeof document < "u" ? document : void 0),
    typeof e > "u")
        return null;
    try {
        return e.activeElement || e.body
    } catch {
        return e.body
    }
}
function di(e, t) {
    var n = t.checked;
    return se({}, t, {
        defaultChecked: void 0,
        defaultValue: void 0,
        value: void 0,
        checked: n ?? e._wrapperState.initialChecked
    })
}
function ku(e, t) {
    var n = t.defaultValue == null ? "" : t.defaultValue
      , r = t.checked != null ? t.checked : t.defaultChecked;
    n = $t(t.value != null ? t.value : n),
    e._wrapperState = {
        initialChecked: r,
        initialValue: n,
        controlled: t.type === "checkbox" || t.type === "radio" ? t.checked != null : t.value != null
    }
}
function Ka(e, t) {
    t = t.checked,
    t != null && ls(e, "checked", t, !1)
}
function fi(e, t) {
    Ka(e, t);
    var n = $t(t.value)
      , r = t.type;
    if (n != null)
        r === "number" ? (n === 0 && e.value === "" || e.value != n) && (e.value = "" + n) : e.value !== "" + n && (e.value = "" + n);
    else if (r === "submit" || r === "reset") {
        e.removeAttribute("value");
        return
    }
    t.hasOwnProperty("value") ? pi(e, t.type, n) : t.hasOwnProperty("defaultValue") && pi(e, t.type, $t(t.defaultValue)),
    t.checked == null && t.defaultChecked != null && (e.defaultChecked = !!t.defaultChecked)
}
function wu(e, t, n) {
    if (t.hasOwnProperty("value") || t.hasOwnProperty("defaultValue")) {
        var r = t.type;
        if (!(r !== "submit" && r !== "reset" || t.value !== void 0 && t.value !== null))
            return;
        t = "" + e._wrapperState.initialValue,
        n || t === e.value || (e.value = t),
        e.defaultValue = t
    }
    n = e.name,
    n !== "" && (e.name = ""),
    e.defaultChecked = !!e._wrapperState.initialChecked,
    n !== "" && (e.name = n)
}
function pi(e, t, n) {
    (t !== "number" || Ll(e.ownerDocument) !== e) && (n == null ? e.defaultValue = "" + e._wrapperState.initialValue : e.defaultValue !== "" + n && (e.defaultValue = "" + n))
}
var ir = Array.isArray;
function Fn(e, t, n, r) {
    if (e = e.options,
    t) {
        t = {};
        for (var l = 0; l < n.length; l++)
            t["$" + n[l]] = !0;
        for (n = 0; n < e.length; n++)
            l = t.hasOwnProperty("$" + e[n].value),
            e[n].selected !== l && (e[n].selected = l),
            l && r && (e[n].defaultSelected = !0)
    } else {
        for (n = "" + $t(n),
        t = null,
        l = 0; l < e.length; l++) {
            if (e[l].value === n) {
                e[l].selected = !0,
                r && (e[l].defaultSelected = !0);
                return
            }
            t !== null || e[l].disabled || (t = e[l])
        }
        t !== null && (t.selected = !0)
    }
}
function hi(e, t) {
    if (t.dangerouslySetInnerHTML != null)
        throw Error(w(91));
    return se({}, t, {
        value: void 0,
        defaultValue: void 0,
        children: "" + e._wrapperState.initialValue
    })
}
function Cu(e, t) {
    var n = t.value;
    if (n == null) {
        if (n = t.children,
        t = t.defaultValue,
        n != null) {
            if (t != null)
                throw Error(w(92));
            if (ir(n)) {
                if (1 < n.length)
                    throw Error(w(93));
                n = n[0]
            }
            t = n
        }
        t == null && (t = ""),
        n = t
    }
    e._wrapperState = {
        initialValue: $t(n)
    }
}
function Ya(e, t) {
    var n = $t(t.value)
      , r = $t(t.defaultValue);
    n != null && (n = "" + n,
    n !== e.value && (e.value = n),
    t.defaultValue == null && e.defaultValue !== n && (e.defaultValue = n)),
    r != null && (e.defaultValue = "" + r)
}
function ju(e) {
    var t = e.textContent;
    t === e._wrapperState.initialValue && t !== "" && t !== null && (e.value = t)
}
function Xa(e) {
    switch (e) {
    case "svg":
        return "http://www.w3.org/2000/svg";
    case "math":
        return "http://www.w3.org/1998/Math/MathML";
    default:
        return "http://www.w3.org/1999/xhtml"
    }
}
function mi(e, t) {
    return e == null || e === "http://www.w3.org/1999/xhtml" ? Xa(t) : e === "http://www.w3.org/2000/svg" && t === "foreignObject" ? "http://www.w3.org/1999/xhtml" : e
}
var el, Ga = function(e) {
    return typeof MSApp < "u" && MSApp.execUnsafeLocalFunction ? function(t, n, r, l) {
        MSApp.execUnsafeLocalFunction(function() {
            return e(t, n, r, l)
        })
    }
    : e
}(function(e, t) {
    if (e.namespaceURI !== "http://www.w3.org/2000/svg" || "innerHTML"in e)
        e.innerHTML = t;
    else {
        for (el = el || document.createElement("div"),
        el.innerHTML = "<svg>" + t.valueOf().toString() + "</svg>",
        t = el.firstChild; e.firstChild; )
            e.removeChild(e.firstChild);
        for (; t.firstChild; )
            e.appendChild(t.firstChild)
    }
});
function xr(e, t) {
    if (t) {
        var n = e.firstChild;
        if (n && n === e.lastChild && n.nodeType === 3) {
            n.nodeValue = t;
            return
        }
    }
    e.textContent = t
}
var ar = {
    animationIterationCount: !0,
    aspectRatio: !0,
    borderImageOutset: !0,
    borderImageSlice: !0,
    borderImageWidth: !0,
    boxFlex: !0,
    boxFlexGroup: !0,
    boxOrdinalGroup: !0,
    columnCount: !0,
    columns: !0,
    flex: !0,
    flexGrow: !0,
    flexPositive: !0,
    flexShrink: !0,
    flexNegative: !0,
    flexOrder: !0,
    gridArea: !0,
    gridRow: !0,
    gridRowEnd: !0,
    gridRowSpan: !0,
    gridRowStart: !0,
    gridColumn: !0,
    gridColumnEnd: !0,
    gridColumnSpan: !0,
    gridColumnStart: !0,
    fontWeight: !0,
    lineClamp: !0,
    lineHeight: !0,
    opacity: !0,
    order: !0,
    orphans: !0,
    tabSize: !0,
    widows: !0,
    zIndex: !0,
    zoom: !0,
    fillOpacity: !0,
    floodOpacity: !0,
    stopOpacity: !0,
    strokeDasharray: !0,
    strokeDashoffset: !0,
    strokeMiterlimit: !0,
    strokeOpacity: !0,
    strokeWidth: !0
}
  , Xf = ["Webkit", "ms", "Moz", "O"];
Object.keys(ar).forEach(function(e) {
    Xf.forEach(function(t) {
        t = t + e.charAt(0).toUpperCase() + e.substring(1),
        ar[t] = ar[e]
    })
});
function Ja(e, t, n) {
    return t == null || typeof t == "boolean" || t === "" ? "" : n || typeof t != "number" || t === 0 || ar.hasOwnProperty(e) && ar[e] ? ("" + t).trim() : t + "px"
}
function Za(e, t) {
    e = e.style;
    for (var n in t)
        if (t.hasOwnProperty(n)) {
            var r = n.indexOf("--") === 0
              , l = Ja(n, t[n], r);
            n === "float" && (n = "cssFloat"),
            r ? e.setProperty(n, l) : e[n] = l
        }
}
var Gf = se({
    menuitem: !0
}, {
    area: !0,
    base: !0,
    br: !0,
    col: !0,
    embed: !0,
    hr: !0,
    img: !0,
    input: !0,
    keygen: !0,
    link: !0,
    meta: !0,
    param: !0,
    source: !0,
    track: !0,
    wbr: !0
});
function yi(e, t) {
    if (t) {
        if (Gf[e] && (t.children != null || t.dangerouslySetInnerHTML != null))
            throw Error(w(137, e));
        if (t.dangerouslySetInnerHTML != null) {
            if (t.children != null)
                throw Error(w(60));
            if (typeof t.dangerouslySetInnerHTML != "object" || !("__html"in t.dangerouslySetInnerHTML))
                throw Error(w(61))
        }
        if (t.style != null && typeof t.style != "object")
            throw Error(w(62))
    }
}
function gi(e, t) {
    if (e.indexOf("-") === -1)
        return typeof t.is == "string";
    switch (e) {
    case "annotation-xml":
    case "color-profile":
    case "font-face":
    case "font-face-src":
    case "font-face-uri":
    case "font-face-format":
    case "font-face-name":
    case "missing-glyph":
        return !1;
    default:
        return !0
    }
}
var vi = null;
function us(e) {
    return e = e.target || e.srcElement || window,
    e.correspondingUseElement && (e = e.correspondingUseElement),
    e.nodeType === 3 ? e.parentNode : e
}
var xi = null
  , In = null
  , Rn = null;
function Eu(e) {
    if (e = Ar(e)) {
        if (typeof xi != "function")
            throw Error(w(280));
        var t = e.stateNode;
        t && (t = ro(t),
        xi(e.stateNode, e.type, t))
    }
}
function qa(e) {
    In ? Rn ? Rn.push(e) : Rn = [e] : In = e
}
function ba() {
    if (In) {
        var e = In
          , t = Rn;
        if (Rn = In = null,
        Eu(e),
        t)
            for (e = 0; e < t.length; e++)
                Eu(t[e])
    }
}
function ec(e, t) {
    return e(t)
}
function tc() {}
var Fo = !1;
function nc(e, t, n) {
    if (Fo)
        return e(t, n);
    Fo = !0;
    try {
        return ec(e, t, n)
    } finally {
        Fo = !1,
        (In !== null || Rn !== null) && (tc(),
        ba())
    }
}
function Sr(e, t) {
    var n = e.stateNode;
    if (n === null)
        return null;
    var r = ro(n);
    if (r === null)
        return null;
    n = r[t];
    e: switch (t) {
    case "onClick":
    case "onClickCapture":
    case "onDoubleClick":
    case "onDoubleClickCapture":
    case "onMouseDown":
    case "onMouseDownCapture":
    case "onMouseMove":
    case "onMouseMoveCapture":
    case "onMouseUp":
    case "onMouseUpCapture":
    case "onMouseEnter":
        (r = !r.disabled) || (e = e.type,
        r = !(e === "button" || e === "input" || e === "select" || e === "textarea")),
        e = !r;
        break e;
    default:
        e = !1
    }
    if (e)
        return null;
    if (n && typeof n != "function")
        throw Error(w(231, t, typeof n));
    return n
}
var Si = !1;
if (vt)
    try {
        var Zn = {};
        Object.defineProperty(Zn, "passive", {
            get: function() {
                Si = !0
            }
        }),
        window.addEventListener("test", Zn, Zn),
        window.removeEventListener("test", Zn, Zn)
    } catch {
        Si = !1
    }
function Jf(e, t, n, r, l, o, i, u, c) {
    var f = Array.prototype.slice.call(arguments, 3);
    try {
        t.apply(n, f)
    } catch (v) {
        this.onError(v)
    }
}
var cr = !1
  , Tl = null
  , Pl = !1
  , ki = null
  , Zf = {
    onError: function(e) {
        cr = !0,
        Tl = e
    }
};
function qf(e, t, n, r, l, o, i, u, c) {
    cr = !1,
    Tl = null,
    Jf.apply(Zf, arguments)
}
function bf(e, t, n, r, l, o, i, u, c) {
    if (qf.apply(this, arguments),
    cr) {
        if (cr) {
            var f = Tl;
            cr = !1,
            Tl = null
        } else
            throw Error(w(198));
        Pl || (Pl = !0,
        ki = f)
    }
}
function cn(e) {
    var t = e
      , n = e;
    if (e.alternate)
        for (; t.return; )
            t = t.return;
    else {
        e = t;
        do
            t = e,
            t.flags & 4098 && (n = t.return),
            e = t.return;
        while (e)
    }
    return t.tag === 3 ? n : null
}
function rc(e) {
    if (e.tag === 13) {
        var t = e.memoizedState;
        if (t === null && (e = e.alternate,
        e !== null && (t = e.memoizedState)),
        t !== null)
            return t.dehydrated
    }
    return null
}
function zu(e) {
    if (cn(e) !== e)
        throw Error(w(188))
}
function ep(e) {
    var t = e.alternate;
    if (!t) {
        if (t = cn(e),
        t === null)
            throw Error(w(188));
        return t !== e ? null : e
    }
    for (var n = e, r = t; ; ) {
        var l = n.return;
        if (l === null)
            break;
        var o = l.alternate;
        if (o === null) {
            if (r = l.return,
            r !== null) {
                n = r;
                continue
            }
            break
        }
        if (l.child === o.child) {
            for (o = l.child; o; ) {
                if (o === n)
                    return zu(l),
                    e;
                if (o === r)
                    return zu(l),
                    t;
                o = o.sibling
            }
            throw Error(w(188))
        }
        if (n.return !== r.return)
            n = l,
            r = o;
        else {
            for (var i = !1, u = l.child; u; ) {
                if (u === n) {
                    i = !0,
                    n = l,
                    r = o;
                    break
                }
                if (u === r) {
                    i = !0,
                    r = l,
                    n = o;
                    break
                }
                u = u.sibling
            }
            if (!i) {
                for (u = o.child; u; ) {
                    if (u === n) {
                        i = !0,
                        n = o,
                        r = l;
                        break
                    }
                    if (u === r) {
                        i = !0,
                        r = o,
                        n = l;
                        break
                    }
                    u = u.sibling
                }
                if (!i)
                    throw Error(w(189))
            }
        }
        if (n.alternate !== r)
            throw Error(w(190))
    }
    if (n.tag !== 3)
        throw Error(w(188));
    return n.stateNode.current === n ? e : t
}
function lc(e) {
    return e = ep(e),
    e !== null ? oc(e) : null
}
function oc(e) {
    if (e.tag === 5 || e.tag === 6)
        return e;
    for (e = e.child; e !== null; ) {
        var t = oc(e);
        if (t !== null)
            return t;
        e = e.sibling
    }
    return null
}
var ic = Be.unstable_scheduleCallback
  , _u = Be.unstable_cancelCallback
  , tp = Be.unstable_shouldYield
  , np = Be.unstable_requestPaint
  , ae = Be.unstable_now
  , rp = Be.unstable_getCurrentPriorityLevel
  , as = Be.unstable_ImmediatePriority
  , sc = Be.unstable_UserBlockingPriority
  , Nl = Be.unstable_NormalPriority
  , lp = Be.unstable_LowPriority
  , uc = Be.unstable_IdlePriority
  , bl = null
  , at = null;
function op(e) {
    if (at && typeof at.onCommitFiberRoot == "function")
        try {
            at.onCommitFiberRoot(bl, e, void 0, (e.current.flags & 128) === 128)
        } catch {}
}
var et = Math.clz32 ? Math.clz32 : up
  , ip = Math.log
  , sp = Math.LN2;
function up(e) {
    return e >>>= 0,
    e === 0 ? 32 : 31 - (ip(e) / sp | 0) | 0
}
var tl = 64
  , nl = 4194304;
function sr(e) {
    switch (e & -e) {
    case 1:
        return 1;
    case 2:
        return 2;
    case 4:
        return 4;
    case 8:
        return 8;
    case 16:
        return 16;
    case 32:
        return 32;
    case 64:
    case 128:
    case 256:
    case 512:
    case 1024:
    case 2048:
    case 4096:
    case 8192:
    case 16384:
    case 32768:
    case 65536:
    case 131072:
    case 262144:
    case 524288:
    case 1048576:
    case 2097152:
        return e & 4194240;
    case 4194304:
    case 8388608:
    case 16777216:
    case 33554432:
    case 67108864:
        return e & 130023424;
    case 134217728:
        return 134217728;
    case 268435456:
        return 268435456;
    case 536870912:
        return 536870912;
    case 1073741824:
        return 1073741824;
    default:
        return e
    }
}
function Fl(e, t) {
    var n = e.pendingLanes;
    if (n === 0)
        return 0;
    var r = 0
      , l = e.suspendedLanes
      , o = e.pingedLanes
      , i = n & 268435455;
    if (i !== 0) {
        var u = i & ~l;
        u !== 0 ? r = sr(u) : (o &= i,
        o !== 0 && (r = sr(o)))
    } else
        i = n & ~l,
        i !== 0 ? r = sr(i) : o !== 0 && (r = sr(o));
    if (r === 0)
        return 0;
    if (t !== 0 && t !== r && !(t & l) && (l = r & -r,
    o = t & -t,
    l >= o || l === 16 && (o & 4194240) !== 0))
        return t;
    if (r & 4 && (r |= n & 16),
    t = e.entangledLanes,
    t !== 0)
        for (e = e.entanglements,
        t &= r; 0 < t; )
            n = 31 - et(t),
            l = 1 << n,
            r |= e[n],
            t &= ~l;
    return r
}
function ap(e, t) {
    switch (e) {
    case 1:
    case 2:
    case 4:
        return t + 250;
    case 8:
    case 16:
    case 32:
    case 64:
    case 128:
    case 256:
    case 512:
    case 1024:
    case 2048:
    case 4096:
    case 8192:
    case 16384:
    case 32768:
    case 65536:
    case 131072:
    case 262144:
    case 524288:
    case 1048576:
    case 2097152:
        return t + 5e3;
    case 4194304:
    case 8388608:
    case 16777216:
    case 33554432:
    case 67108864:
        return -1;
    case 134217728:
    case 268435456:
    case 536870912:
    case 1073741824:
        return -1;
    default:
        return -1
    }
}
function cp(e, t) {
    for (var n = e.suspendedLanes, r = e.pingedLanes, l = e.expirationTimes, o = e.pendingLanes; 0 < o; ) {
        var i = 31 - et(o)
          , u = 1 << i
          , c = l[i];
        c === -1 ? (!(u & n) || u & r) && (l[i] = ap(u, t)) : c <= t && (e.expiredLanes |= u),
        o &= ~u
    }
}
function wi(e) {
    return e = e.pendingLanes & -1073741825,
    e !== 0 ? e : e & 1073741824 ? 1073741824 : 0
}
function ac() {
    var e = tl;
    return tl <<= 1,
    !(tl & 4194240) && (tl = 64),
    e
}
function Io(e) {
    for (var t = [], n = 0; 31 > n; n++)
        t.push(e);
    return t
}
function Or(e, t, n) {
    e.pendingLanes |= t,
    t !== 536870912 && (e.suspendedLanes = 0,
    e.pingedLanes = 0),
    e = e.eventTimes,
    t = 31 - et(t),
    e[t] = n
}
function dp(e, t) {
    var n = e.pendingLanes & ~t;
    e.pendingLanes = t,
    e.suspendedLanes = 0,
    e.pingedLanes = 0,
    e.expiredLanes &= t,
    e.mutableReadLanes &= t,
    e.entangledLanes &= t,
    t = e.entanglements;
    var r = e.eventTimes;
    for (e = e.expirationTimes; 0 < n; ) {
        var l = 31 - et(n)
          , o = 1 << l;
        t[l] = 0,
        r[l] = -1,
        e[l] = -1,
        n &= ~o
    }
}
function cs(e, t) {
    var n = e.entangledLanes |= t;
    for (e = e.entanglements; n; ) {
        var r = 31 - et(n)
          , l = 1 << r;
        l & t | e[r] & t && (e[r] |= t),
        n &= ~l
    }
}
var G = 0;
function cc(e) {
    return e &= -e,
    1 < e ? 4 < e ? e & 268435455 ? 16 : 536870912 : 4 : 1
}
var dc, ds, fc, pc, hc, Ci = !1, rl = [], It = null, Rt = null, Dt = null, kr = new Map, wr = new Map, Tt = [], fp = "mousedown mouseup touchcancel touchend touchstart auxclick dblclick pointercancel pointerdown pointerup dragend dragstart drop compositionend compositionstart keydown keypress keyup input textInput copy cut paste click change contextmenu reset submit".split(" ");
function Lu(e, t) {
    switch (e) {
    case "focusin":
    case "focusout":
        It = null;
        break;
    case "dragenter":
    case "dragleave":
        Rt = null;
        break;
    case "mouseover":
    case "mouseout":
        Dt = null;
        break;
    case "pointerover":
    case "pointerout":
        kr.delete(t.pointerId);
        break;
    case "gotpointercapture":
    case "lostpointercapture":
        wr.delete(t.pointerId)
    }
}
function qn(e, t, n, r, l, o) {
    return e === null || e.nativeEvent !== o ? (e = {
        blockedOn: t,
        domEventName: n,
        eventSystemFlags: r,
        nativeEvent: o,
        targetContainers: [l]
    },
    t !== null && (t = Ar(t),
    t !== null && ds(t)),
    e) : (e.eventSystemFlags |= r,
    t = e.targetContainers,
    l !== null && t.indexOf(l) === -1 && t.push(l),
    e)
}
function pp(e, t, n, r, l) {
    switch (t) {
    case "focusin":
        return It = qn(It, e, t, n, r, l),
        !0;
    case "dragenter":
        return Rt = qn(Rt, e, t, n, r, l),
        !0;
    case "mouseover":
        return Dt = qn(Dt, e, t, n, r, l),
        !0;
    case "pointerover":
        var o = l.pointerId;
        return kr.set(o, qn(kr.get(o) || null, e, t, n, r, l)),
        !0;
    case "gotpointercapture":
        return o = l.pointerId,
        wr.set(o, qn(wr.get(o) || null, e, t, n, r, l)),
        !0
    }
    return !1
}
function mc(e) {
    var t = Zt(e.target);
    if (t !== null) {
        var n = cn(t);
        if (n !== null) {
            if (t = n.tag,
            t === 13) {
                if (t = rc(n),
                t !== null) {
                    e.blockedOn = t,
                    hc(e.priority, function() {
                        fc(n)
                    });
                    return
                }
            } else if (t === 3 && n.stateNode.current.memoizedState.isDehydrated) {
                e.blockedOn = n.tag === 3 ? n.stateNode.containerInfo : null;
                return
            }
        }
    }
    e.blockedOn = null
}
function vl(e) {
    if (e.blockedOn !== null)
        return !1;
    for (var t = e.targetContainers; 0 < t.length; ) {
        var n = ji(e.domEventName, e.eventSystemFlags, t[0], e.nativeEvent);
        if (n === null) {
            n = e.nativeEvent;
            var r = new n.constructor(n.type,n);
            vi = r,
            n.target.dispatchEvent(r),
            vi = null
        } else
            return t = Ar(n),
            t !== null && ds(t),
            e.blockedOn = n,
            !1;
        t.shift()
    }
    return !0
}
function Tu(e, t, n) {
    vl(e) && n.delete(t)
}
function hp() {
    Ci = !1,
    It !== null && vl(It) && (It = null),
    Rt !== null && vl(Rt) && (Rt = null),
    Dt !== null && vl(Dt) && (Dt = null),
    kr.forEach(Tu),
    wr.forEach(Tu)
}
function bn(e, t) {
    e.blockedOn === t && (e.blockedOn = null,
    Ci || (Ci = !0,
    Be.unstable_scheduleCallback(Be.unstable_NormalPriority, hp)))
}
function Cr(e) {
    function t(l) {
        return bn(l, e)
    }
    if (0 < rl.length) {
        bn(rl[0], e);
        for (var n = 1; n < rl.length; n++) {
            var r = rl[n];
            r.blockedOn === e && (r.blockedOn = null)
        }
    }
    for (It !== null && bn(It, e),
    Rt !== null && bn(Rt, e),
    Dt !== null && bn(Dt, e),
    kr.forEach(t),
    wr.forEach(t),
    n = 0; n < Tt.length; n++)
        r = Tt[n],
        r.blockedOn === e && (r.blockedOn = null);
    for (; 0 < Tt.length && (n = Tt[0],
    n.blockedOn === null); )
        mc(n),
        n.blockedOn === null && Tt.shift()
}
var Dn = wt.ReactCurrentBatchConfig
  , Il = !0;
function mp(e, t, n, r) {
    var l = G
      , o = Dn.transition;
    Dn.transition = null;
    try {
        G = 1,
        fs(e, t, n, r)
    } finally {
        G = l,
        Dn.transition = o
    }
}
function yp(e, t, n, r) {
    var l = G
      , o = Dn.transition;
    Dn.transition = null;
    try {
        G = 4,
        fs(e, t, n, r)
    } finally {
        G = l,
        Dn.transition = o
    }
}
function fs(e, t, n, r) {
    if (Il) {
        var l = ji(e, t, n, r);
        if (l === null)
            Ho(e, t, r, Rl, n),
            Lu(e, r);
        else if (pp(l, e, t, n, r))
            r.stopPropagation();
        else if (Lu(e, r),
        t & 4 && -1 < fp.indexOf(e)) {
            for (; l !== null; ) {
                var o = Ar(l);
                if (o !== null && dc(o),
                o = ji(e, t, n, r),
                o === null && Ho(e, t, r, Rl, n),
                o === l)
                    break;
                l = o
            }
            l !== null && r.stopPropagation()
        } else
            Ho(e, t, r, null, n)
    }
}
var Rl = null;
function ji(e, t, n, r) {
    if (Rl = null,
    e = us(r),
    e = Zt(e),
    e !== null)
        if (t = cn(e),
        t === null)
            e = null;
        else if (n = t.tag,
        n === 13) {
            if (e = rc(t),
            e !== null)
                return e;
            e = null
        } else if (n === 3) {
            if (t.stateNode.current.memoizedState.isDehydrated)
                return t.tag === 3 ? t.stateNode.containerInfo : null;
            e = null
        } else
            t !== e && (e = null);
    return Rl = e,
    null
}
function yc(e) {
    switch (e) {
    case "cancel":
    case "click":
    case "close":
    case "contextmenu":
    case "copy":
    case "cut":
    case "auxclick":
    case "dblclick":
    case "dragend":
    case "dragstart":
    case "drop":
    case "focusin":
    case "focusout":
    case "input":
    case "invalid":
    case "keydown":
    case "keypress":
    case "keyup":
    case "mousedown":
    case "mouseup":
    case "paste":
    case "pause":
    case "play":
    case "pointercancel":
    case "pointerdown":
    case "pointerup":
    case "ratechange":
    case "reset":
    case "resize":
    case "seeked":
    case "submit":
    case "touchcancel":
    case "touchend":
    case "touchstart":
    case "volumechange":
    case "change":
    case "selectionchange":
    case "textInput":
    case "compositionstart":
    case "compositionend":
    case "compositionupdate":
    case "beforeblur":
    case "afterblur":
    case "beforeinput":
    case "blur":
    case "fullscreenchange":
    case "focus":
    case "hashchange":
    case "popstate":
    case "select":
    case "selectstart":
        return 1;
    case "drag":
    case "dragenter":
    case "dragexit":
    case "dragleave":
    case "dragover":
    case "mousemove":
    case "mouseout":
    case "mouseover":
    case "pointermove":
    case "pointerout":
    case "pointerover":
    case "scroll":
    case "toggle":
    case "touchmove":
    case "wheel":
    case "mouseenter":
    case "mouseleave":
    case "pointerenter":
    case "pointerleave":
        return 4;
    case "message":
        switch (rp()) {
        case as:
            return 1;
        case sc:
            return 4;
        case Nl:
        case lp:
            return 16;
        case uc:
            return 536870912;
        default:
            return 16
        }
    default:
        return 16
    }
}
var Nt = null
  , ps = null
  , xl = null;
function gc() {
    if (xl)
        return xl;
    var e, t = ps, n = t.length, r, l = "value"in Nt ? Nt.value : Nt.textContent, o = l.length;
    for (e = 0; e < n && t[e] === l[e]; e++)
        ;
    var i = n - e;
    for (r = 1; r <= i && t[n - r] === l[o - r]; r++)
        ;
    return xl = l.slice(e, 1 < r ? 1 - r : void 0)
}
function Sl(e) {
    var t = e.keyCode;
    return "charCode"in e ? (e = e.charCode,
    e === 0 && t === 13 && (e = 13)) : e = t,
    e === 10 && (e = 13),
    32 <= e || e === 13 ? e : 0
}
function ll() {
    return !0
}
function Pu() {
    return !1
}
function Ue(e) {
    function t(n, r, l, o, i) {
        this._reactName = n,
        this._targetInst = l,
        this.type = r,
        this.nativeEvent = o,
        this.target = i,
        this.currentTarget = null;
        for (var u in e)
            e.hasOwnProperty(u) && (n = e[u],
            this[u] = n ? n(o) : o[u]);
        return this.isDefaultPrevented = (o.defaultPrevented != null ? o.defaultPrevented : o.returnValue === !1) ? ll : Pu,
        this.isPropagationStopped = Pu,
        this
    }
    return se(t.prototype, {
        preventDefault: function() {
            this.defaultPrevented = !0;
            var n = this.nativeEvent;
            n && (n.preventDefault ? n.preventDefault() : typeof n.returnValue != "unknown" && (n.returnValue = !1),
            this.isDefaultPrevented = ll)
        },
        stopPropagation: function() {
            var n = this.nativeEvent;
            n && (n.stopPropagation ? n.stopPropagation() : typeof n.cancelBubble != "unknown" && (n.cancelBubble = !0),
            this.isPropagationStopped = ll)
        },
        persist: function() {},
        isPersistent: ll
    }),
    t
}
var Kn = {
    eventPhase: 0,
    bubbles: 0,
    cancelable: 0,
    timeStamp: function(e) {
        return e.timeStamp || Date.now()
    },
    defaultPrevented: 0,
    isTrusted: 0
}, hs = Ue(Kn), Mr = se({}, Kn, {
    view: 0,
    detail: 0
}), gp = Ue(Mr), Ro, Do, er, eo = se({}, Mr, {
    screenX: 0,
    screenY: 0,
    clientX: 0,
    clientY: 0,
    pageX: 0,
    pageY: 0,
    ctrlKey: 0,
    shiftKey: 0,
    altKey: 0,
    metaKey: 0,
    getModifierState: ms,
    button: 0,
    buttons: 0,
    relatedTarget: function(e) {
        return e.relatedTarget === void 0 ? e.fromElement === e.srcElement ? e.toElement : e.fromElement : e.relatedTarget
    },
    movementX: function(e) {
        return "movementX"in e ? e.movementX : (e !== er && (er && e.type === "mousemove" ? (Ro = e.screenX - er.screenX,
        Do = e.screenY - er.screenY) : Do = Ro = 0,
        er = e),
        Ro)
    },
    movementY: function(e) {
        return "movementY"in e ? e.movementY : Do
    }
}), Nu = Ue(eo), vp = se({}, eo, {
    dataTransfer: 0
}), xp = Ue(vp), Sp = se({}, Mr, {
    relatedTarget: 0
}), Oo = Ue(Sp), kp = se({}, Kn, {
    animationName: 0,
    elapsedTime: 0,
    pseudoElement: 0
}), wp = Ue(kp), Cp = se({}, Kn, {
    clipboardData: function(e) {
        return "clipboardData"in e ? e.clipboardData : window.clipboardData
    }
}), jp = Ue(Cp), Ep = se({}, Kn, {
    data: 0
}), Fu = Ue(Ep), zp = {
    Esc: "Escape",
    Spacebar: " ",
    Left: "ArrowLeft",
    Up: "ArrowUp",
    Right: "ArrowRight",
    Down: "ArrowDown",
    Del: "Delete",
    Win: "OS",
    Menu: "ContextMenu",
    Apps: "ContextMenu",
    Scroll: "ScrollLock",
    MozPrintableKey: "Unidentified"
}, _p = {
    8: "Backspace",
    9: "Tab",
    12: "Clear",
    13: "Enter",
    16: "Shift",
    17: "Control",
    18: "Alt",
    19: "Pause",
    20: "CapsLock",
    27: "Escape",
    32: " ",
    33: "PageUp",
    34: "PageDown",
    35: "End",
    36: "Home",
    37: "ArrowLeft",
    38: "ArrowUp",
    39: "ArrowRight",
    40: "ArrowDown",
    45: "Insert",
    46: "Delete",
    112: "F1",
    113: "F2",
    114: "F3",
    115: "F4",
    116: "F5",
    117: "F6",
    118: "F7",
    119: "F8",
    120: "F9",
    121: "F10",
    122: "F11",
    123: "F12",
    144: "NumLock",
    145: "ScrollLock",
    224: "Meta"
}, Lp = {
    Alt: "altKey",
    Control: "ctrlKey",
    Meta: "metaKey",
    Shift: "shiftKey"
};
function Tp(e) {
    var t = this.nativeEvent;
    return t.getModifierState ? t.getModifierState(e) : (e = Lp[e]) ? !!t[e] : !1
}
function ms() {
    return Tp
}
var Pp = se({}, Mr, {
    key: function(e) {
        if (e.key) {
            var t = zp[e.key] || e.key;
            if (t !== "Unidentified")
                return t
        }
        return e.type === "keypress" ? (e = Sl(e),
        e === 13 ? "Enter" : String.fromCharCode(e)) : e.type === "keydown" || e.type === "keyup" ? _p[e.keyCode] || "Unidentified" : ""
    },
    code: 0,
    location: 0,
    ctrlKey: 0,
    shiftKey: 0,
    altKey: 0,
    metaKey: 0,
    repeat: 0,
    locale: 0,
    getModifierState: ms,
    charCode: function(e) {
        return e.type === "keypress" ? Sl(e) : 0
    },
    keyCode: function(e) {
        return e.type === "keydown" || e.type === "keyup" ? e.keyCode : 0
    },
    which: function(e) {
        return e.type === "keypress" ? Sl(e) : e.type === "keydown" || e.type === "keyup" ? e.keyCode : 0
    }
})
  , Np = Ue(Pp)
  , Fp = se({}, eo, {
    pointerId: 0,
    width: 0,
    height: 0,
    pressure: 0,
    tangentialPressure: 0,
    tiltX: 0,
    tiltY: 0,
    twist: 0,
    pointerType: 0,
    isPrimary: 0
})
  , Iu = Ue(Fp)
  , Ip = se({}, Mr, {
    touches: 0,
    targetTouches: 0,
    changedTouches: 0,
    altKey: 0,
    metaKey: 0,
    ctrlKey: 0,
    shiftKey: 0,
    getModifierState: ms
})
  , Rp = Ue(Ip)
  , Dp = se({}, Kn, {
    propertyName: 0,
    elapsedTime: 0,
    pseudoElement: 0
})
  , Op = Ue(Dp)
  , Mp = se({}, eo, {
    deltaX: function(e) {
        return "deltaX"in e ? e.deltaX : "wheelDeltaX"in e ? -e.wheelDeltaX : 0
    },
    deltaY: function(e) {
        return "deltaY"in e ? e.deltaY : "wheelDeltaY"in e ? -e.wheelDeltaY : "wheelDelta"in e ? -e.wheelDelta : 0
    },
    deltaZ: 0,
    deltaMode: 0
})
  , Ap = Ue(Mp)
  , Wp = [9, 13, 27, 32]
  , ys = vt && "CompositionEvent"in window
  , dr = null;
vt && "documentMode"in document && (dr = document.documentMode);
var Bp = vt && "TextEvent"in window && !dr
  , vc = vt && (!ys || dr && 8 < dr && 11 >= dr)
  , Ru = " "
  , Du = !1;
function xc(e, t) {
    switch (e) {
    case "keyup":
        return Wp.indexOf(t.keyCode) !== -1;
    case "keydown":
        return t.keyCode !== 229;
    case "keypress":
    case "mousedown":
    case "focusout":
        return !0;
    default:
        return !1
    }
}
function Sc(e) {
    return e = e.detail,
    typeof e == "object" && "data"in e ? e.data : null
}
var wn = !1;
function $p(e, t) {
    switch (e) {
    case "compositionend":
        return Sc(t);
    case "keypress":
        return t.which !== 32 ? null : (Du = !0,
        Ru);
    case "textInput":
        return e = t.data,
        e === Ru && Du ? null : e;
    default:
        return null
    }
}
function Up(e, t) {
    if (wn)
        return e === "compositionend" || !ys && xc(e, t) ? (e = gc(),
        xl = ps = Nt = null,
        wn = !1,
        e) : null;
    switch (e) {
    case "paste":
        return null;
    case "keypress":
        if (!(t.ctrlKey || t.altKey || t.metaKey) || t.ctrlKey && t.altKey) {
            if (t.char && 1 < t.char.length)
                return t.char;
            if (t.which)
                return String.fromCharCode(t.which)
        }
        return null;
    case "compositionend":
        return vc && t.locale !== "ko" ? null : t.data;
    default:
        return null
    }
}
var Hp = {
    color: !0,
    date: !0,
    datetime: !0,
    "datetime-local": !0,
    email: !0,
    month: !0,
    number: !0,
    password: !0,
    range: !0,
    search: !0,
    tel: !0,
    text: !0,
    time: !0,
    url: !0,
    week: !0
};
function Ou(e) {
    var t = e && e.nodeName && e.nodeName.toLowerCase();
    return t === "input" ? !!Hp[e.type] : t === "textarea"
}
function kc(e, t, n, r) {
    qa(r),
    t = Dl(t, "onChange"),
    0 < t.length && (n = new hs("onChange","change",null,n,r),
    e.push({
        event: n,
        listeners: t
    }))
}
var fr = null
  , jr = null;
function Vp(e) {
    Fc(e, 0)
}
function to(e) {
    var t = En(e);
    if (Qa(t))
        return e
}
function Qp(e, t) {
    if (e === "change")
        return t
}
var wc = !1;
if (vt) {
    var Mo;
    if (vt) {
        var Ao = "oninput"in document;
        if (!Ao) {
            var Mu = document.createElement("div");
            Mu.setAttribute("oninput", "return;"),
            Ao = typeof Mu.oninput == "function"
        }
        Mo = Ao
    } else
        Mo = !1;
    wc = Mo && (!document.documentMode || 9 < document.documentMode)
}
function Au() {
    fr && (fr.detachEvent("onpropertychange", Cc),
    jr = fr = null)
}
function Cc(e) {
    if (e.propertyName === "value" && to(jr)) {
        var t = [];
        kc(t, jr, e, us(e)),
        nc(Vp, t)
    }
}
function Kp(e, t, n) {
    e === "focusin" ? (Au(),
    fr = t,
    jr = n,
    fr.attachEvent("onpropertychange", Cc)) : e === "focusout" && Au()
}
function Yp(e) {
    if (e === "selectionchange" || e === "keyup" || e === "keydown")
        return to(jr)
}
function Xp(e, t) {
    if (e === "click")
        return to(t)
}
function Gp(e, t) {
    if (e === "input" || e === "change")
        return to(t)
}
function Jp(e, t) {
    return e === t && (e !== 0 || 1 / e === 1 / t) || e !== e && t !== t
}
var nt = typeof Object.is == "function" ? Object.is : Jp;
function Er(e, t) {
    if (nt(e, t))
        return !0;
    if (typeof e != "object" || e === null || typeof t != "object" || t === null)
        return !1;
    var n = Object.keys(e)
      , r = Object.keys(t);
    if (n.length !== r.length)
        return !1;
    for (r = 0; r < n.length; r++) {
        var l = n[r];
        if (!ii.call(t, l) || !nt(e[l], t[l]))
            return !1
    }
    return !0
}
function Wu(e) {
    for (; e && e.firstChild; )
        e = e.firstChild;
    return e
}
function Bu(e, t) {
    var n = Wu(e);
    e = 0;
    for (var r; n; ) {
        if (n.nodeType === 3) {
            if (r = e + n.textContent.length,
            e <= t && r >= t)
                return {
                    node: n,
                    offset: t - e
                };
            e = r
        }
        e: {
            for (; n; ) {
                if (n.nextSibling) {
                    n = n.nextSibling;
                    break e
                }
                n = n.parentNode
            }
            n = void 0
        }
        n = Wu(n)
    }
}
function jc(e, t) {
    return e && t ? e === t ? !0 : e && e.nodeType === 3 ? !1 : t && t.nodeType === 3 ? jc(e, t.parentNode) : "contains"in e ? e.contains(t) : e.compareDocumentPosition ? !!(e.compareDocumentPosition(t) & 16) : !1 : !1
}
function Ec() {
    for (var e = window, t = Ll(); t instanceof e.HTMLIFrameElement; ) {
        try {
            var n = typeof t.contentWindow.location.href == "string"
        } catch {
            n = !1
        }
        if (n)
            e = t.contentWindow;
        else
            break;
        t = Ll(e.document)
    }
    return t
}
function gs(e) {
    var t = e && e.nodeName && e.nodeName.toLowerCase();
    return t && (t === "input" && (e.type === "text" || e.type === "search" || e.type === "tel" || e.type === "url" || e.type === "password") || t === "textarea" || e.contentEditable === "true")
}
function Zp(e) {
    var t = Ec()
      , n = e.focusedElem
      , r = e.selectionRange;
    if (t !== n && n && n.ownerDocument && jc(n.ownerDocument.documentElement, n)) {
        if (r !== null && gs(n)) {
            if (t = r.start,
            e = r.end,
            e === void 0 && (e = t),
            "selectionStart"in n)
                n.selectionStart = t,
                n.selectionEnd = Math.min(e, n.value.length);
            else if (e = (t = n.ownerDocument || document) && t.defaultView || window,
            e.getSelection) {
                e = e.getSelection();
                var l = n.textContent.length
                  , o = Math.min(r.start, l);
                r = r.end === void 0 ? o : Math.min(r.end, l),
                !e.extend && o > r && (l = r,
                r = o,
                o = l),
                l = Bu(n, o);
                var i = Bu(n, r);
                l && i && (e.rangeCount !== 1 || e.anchorNode !== l.node || e.anchorOffset !== l.offset || e.focusNode !== i.node || e.focusOffset !== i.offset) && (t = t.createRange(),
                t.setStart(l.node, l.offset),
                e.removeAllRanges(),
                o > r ? (e.addRange(t),
                e.extend(i.node, i.offset)) : (t.setEnd(i.node, i.offset),
                e.addRange(t)))
            }
        }
        for (t = [],
        e = n; e = e.parentNode; )
            e.nodeType === 1 && t.push({
                element: e,
                left: e.scrollLeft,
                top: e.scrollTop
            });
        for (typeof n.focus == "function" && n.focus(),
        n = 0; n < t.length; n++)
            e = t[n],
            e.element.scrollLeft = e.left,
            e.element.scrollTop = e.top
    }
}
var qp = vt && "documentMode"in document && 11 >= document.documentMode
  , Cn = null
  , Ei = null
  , pr = null
  , zi = !1;
function $u(e, t, n) {
    var r = n.window === n ? n.document : n.nodeType === 9 ? n : n.ownerDocument;
    zi || Cn == null || Cn !== Ll(r) || (r = Cn,
    "selectionStart"in r && gs(r) ? r = {
        start: r.selectionStart,
        end: r.selectionEnd
    } : (r = (r.ownerDocument && r.ownerDocument.defaultView || window).getSelection(),
    r = {
        anchorNode: r.anchorNode,
        anchorOffset: r.anchorOffset,
        focusNode: r.focusNode,
        focusOffset: r.focusOffset
    }),
    pr && Er(pr, r) || (pr = r,
    r = Dl(Ei, "onSelect"),
    0 < r.length && (t = new hs("onSelect","select",null,t,n),
    e.push({
        event: t,
        listeners: r
    }),
    t.target = Cn)))
}
function ol(e, t) {
    var n = {};
    return n[e.toLowerCase()] = t.toLowerCase(),
    n["Webkit" + e] = "webkit" + t,
    n["Moz" + e] = "moz" + t,
    n
}
var jn = {
    animationend: ol("Animation", "AnimationEnd"),
    animationiteration: ol("Animation", "AnimationIteration"),
    animationstart: ol("Animation", "AnimationStart"),
    transitionend: ol("Transition", "TransitionEnd")
}
  , Wo = {}
  , zc = {};
vt && (zc = document.createElement("div").style,
"AnimationEvent"in window || (delete jn.animationend.animation,
delete jn.animationiteration.animation,
delete jn.animationstart.animation),
"TransitionEvent"in window || delete jn.transitionend.transition);
function no(e) {
    if (Wo[e])
        return Wo[e];
    if (!jn[e])
        return e;
    var t = jn[e], n;
    for (n in t)
        if (t.hasOwnProperty(n) && n in zc)
            return Wo[e] = t[n];
    return e
}
var _c = no("animationend")
  , Lc = no("animationiteration")
  , Tc = no("animationstart")
  , Pc = no("transitionend")
  , Nc = new Map
  , Uu = "abort auxClick cancel canPlay canPlayThrough click close contextMenu copy cut drag dragEnd dragEnter dragExit dragLeave dragOver dragStart drop durationChange emptied encrypted ended error gotPointerCapture input invalid keyDown keyPress keyUp load loadedData loadedMetadata loadStart lostPointerCapture mouseDown mouseMove mouseOut mouseOver mouseUp paste pause play playing pointerCancel pointerDown pointerMove pointerOut pointerOver pointerUp progress rateChange reset resize seeked seeking stalled submit suspend timeUpdate touchCancel touchEnd touchStart volumeChange scroll toggle touchMove waiting wheel".split(" ");
function Ht(e, t) {
    Nc.set(e, t),
    an(t, [e])
}
for (var Bo = 0; Bo < Uu.length; Bo++) {
    var $o = Uu[Bo]
      , bp = $o.toLowerCase()
      , eh = $o[0].toUpperCase() + $o.slice(1);
    Ht(bp, "on" + eh)
}
Ht(_c, "onAnimationEnd");
Ht(Lc, "onAnimationIteration");
Ht(Tc, "onAnimationStart");
Ht("dblclick", "onDoubleClick");
Ht("focusin", "onFocus");
Ht("focusout", "onBlur");
Ht(Pc, "onTransitionEnd");
An("onMouseEnter", ["mouseout", "mouseover"]);
An("onMouseLeave", ["mouseout", "mouseover"]);
An("onPointerEnter", ["pointerout", "pointerover"]);
An("onPointerLeave", ["pointerout", "pointerover"]);
an("onChange", "change click focusin focusout input keydown keyup selectionchange".split(" "));
an("onSelect", "focusout contextmenu dragend focusin keydown keyup mousedown mouseup selectionchange".split(" "));
an("onBeforeInput", ["compositionend", "keypress", "textInput", "paste"]);
an("onCompositionEnd", "compositionend focusout keydown keypress keyup mousedown".split(" "));
an("onCompositionStart", "compositionstart focusout keydown keypress keyup mousedown".split(" "));
an("onCompositionUpdate", "compositionupdate focusout keydown keypress keyup mousedown".split(" "));
var ur = "abort canplay canplaythrough durationchange emptied encrypted ended error loadeddata loadedmetadata loadstart pause play playing progress ratechange resize seeked seeking stalled suspend timeupdate volumechange waiting".split(" ")
  , th = new Set("cancel close invalid load scroll toggle".split(" ").concat(ur));
function Hu(e, t, n) {
    var r = e.type || "unknown-event";
    e.currentTarget = n,
    bf(r, t, void 0, e),
    e.currentTarget = null
}
function Fc(e, t) {
    t = (t & 4) !== 0;
    for (var n = 0; n < e.length; n++) {
        var r = e[n]
          , l = r.event;
        r = r.listeners;
        e: {
            var o = void 0;
            if (t)
                for (var i = r.length - 1; 0 <= i; i--) {
                    var u = r[i]
                      , c = u.instance
                      , f = u.currentTarget;
                    if (u = u.listener,
                    c !== o && l.isPropagationStopped())
                        break e;
                    Hu(l, u, f),
                    o = c
                }
            else
                for (i = 0; i < r.length; i++) {
                    if (u = r[i],
                    c = u.instance,
                    f = u.currentTarget,
                    u = u.listener,
                    c !== o && l.isPropagationStopped())
                        break e;
                    Hu(l, u, f),
                    o = c
                }
        }
    }
    if (Pl)
        throw e = ki,
        Pl = !1,
        ki = null,
        e
}
function b(e, t) {
    var n = t[Ni];
    n === void 0 && (n = t[Ni] = new Set);
    var r = e + "__bubble";
    n.has(r) || (Ic(t, e, 2, !1),
    n.add(r))
}
function Uo(e, t, n) {
    var r = 0;
    t && (r |= 4),
    Ic(n, e, r, t)
}
var il = "_reactListening" + Math.random().toString(36).slice(2);
function zr(e) {
    if (!e[il]) {
        e[il] = !0,
        Ba.forEach(function(n) {
            n !== "selectionchange" && (th.has(n) || Uo(n, !1, e),
            Uo(n, !0, e))
        });
        var t = e.nodeType === 9 ? e : e.ownerDocument;
        t === null || t[il] || (t[il] = !0,
        Uo("selectionchange", !1, t))
    }
}
function Ic(e, t, n, r) {
    switch (yc(t)) {
    case 1:
        var l = mp;
        break;
    case 4:
        l = yp;
        break;
    default:
        l = fs
    }
    n = l.bind(null, t, n, e),
    l = void 0,
    !Si || t !== "touchstart" && t !== "touchmove" && t !== "wheel" || (l = !0),
    r ? l !== void 0 ? e.addEventListener(t, n, {
        capture: !0,
        passive: l
    }) : e.addEventListener(t, n, !0) : l !== void 0 ? e.addEventListener(t, n, {
        passive: l
    }) : e.addEventListener(t, n, !1)
}
function Ho(e, t, n, r, l) {
    var o = r;
    if (!(t & 1) && !(t & 2) && r !== null)
        e: for (; ; ) {
            if (r === null)
                return;
            var i = r.tag;
            if (i === 3 || i === 4) {
                var u = r.stateNode.containerInfo;
                if (u === l || u.nodeType === 8 && u.parentNode === l)
                    break;
                if (i === 4)
                    for (i = r.return; i !== null; ) {
                        var c = i.tag;
                        if ((c === 3 || c === 4) && (c = i.stateNode.containerInfo,
                        c === l || c.nodeType === 8 && c.parentNode === l))
                            return;
                        i = i.return
                    }
                for (; u !== null; ) {
                    if (i = Zt(u),
                    i === null)
                        return;
                    if (c = i.tag,
                    c === 5 || c === 6) {
                        r = o = i;
                        continue e
                    }
                    u = u.parentNode
                }
            }
            r = r.return
        }
    nc(function() {
        var f = o
          , v = us(n)
          , g = [];
        e: {
            var y = Nc.get(e);
            if (y !== void 0) {
                var C = hs
                  , j = e;
                switch (e) {
                case "keypress":
                    if (Sl(n) === 0)
                        break e;
                case "keydown":
                case "keyup":
                    C = Np;
                    break;
                case "focusin":
                    j = "focus",
                    C = Oo;
                    break;
                case "focusout":
                    j = "blur",
                    C = Oo;
                    break;
                case "beforeblur":
                case "afterblur":
                    C = Oo;
                    break;
                case "click":
                    if (n.button === 2)
                        break e;
                case "auxclick":
                case "dblclick":
                case "mousedown":
                case "mousemove":
                case "mouseup":
                case "mouseout":
                case "mouseover":
                case "contextmenu":
                    C = Nu;
                    break;
                case "drag":
                case "dragend":
                case "dragenter":
                case "dragexit":
                case "dragleave":
                case "dragover":
                case "dragstart":
                case "drop":
                    C = xp;
                    break;
                case "touchcancel":
                case "touchend":
                case "touchmove":
                case "touchstart":
                    C = Rp;
                    break;
                case _c:
                case Lc:
                case Tc:
                    C = wp;
                    break;
                case Pc:
                    C = Op;
                    break;
                case "scroll":
                    C = gp;
                    break;
                case "wheel":
                    C = Ap;
                    break;
                case "copy":
                case "cut":
                case "paste":
                    C = jp;
                    break;
                case "gotpointercapture":
                case "lostpointercapture":
                case "pointercancel":
                case "pointerdown":
                case "pointermove":
                case "pointerout":
                case "pointerover":
                case "pointerup":
                    C = Iu
                }
                var _ = (t & 4) !== 0
                  , Z = !_ && e === "scroll"
                  , p = _ ? y !== null ? y + "Capture" : null : y;
                _ = [];
                for (var d = f, m; d !== null; ) {
                    m = d;
                    var S = m.stateNode;
                    if (m.tag === 5 && S !== null && (m = S,
                    p !== null && (S = Sr(d, p),
                    S != null && _.push(_r(d, S, m)))),
                    Z)
                        break;
                    d = d.return
                }
                0 < _.length && (y = new C(y,j,null,n,v),
                g.push({
                    event: y,
                    listeners: _
                }))
            }
        }
        if (!(t & 7)) {
            e: {
                if (y = e === "mouseover" || e === "pointerover",
                C = e === "mouseout" || e === "pointerout",
                y && n !== vi && (j = n.relatedTarget || n.fromElement) && (Zt(j) || j[xt]))
                    break e;
                if ((C || y) && (y = v.window === v ? v : (y = v.ownerDocument) ? y.defaultView || y.parentWindow : window,
                C ? (j = n.relatedTarget || n.toElement,
                C = f,
                j = j ? Zt(j) : null,
                j !== null && (Z = cn(j),
                j !== Z || j.tag !== 5 && j.tag !== 6) && (j = null)) : (C = null,
                j = f),
                C !== j)) {
                    if (_ = Nu,
                    S = "onMouseLeave",
                    p = "onMouseEnter",
                    d = "mouse",
                    (e === "pointerout" || e === "pointerover") && (_ = Iu,
                    S = "onPointerLeave",
                    p = "onPointerEnter",
                    d = "pointer"),
                    Z = C == null ? y : En(C),
                    m = j == null ? y : En(j),
                    y = new _(S,d + "leave",C,n,v),
                    y.target = Z,
                    y.relatedTarget = m,
                    S = null,
                    Zt(v) === f && (_ = new _(p,d + "enter",j,n,v),
                    _.target = m,
                    _.relatedTarget = Z,
                    S = _),
                    Z = S,
                    C && j)
                        t: {
                            for (_ = C,
                            p = j,
                            d = 0,
                            m = _; m; m = xn(m))
                                d++;
                            for (m = 0,
                            S = p; S; S = xn(S))
                                m++;
                            for (; 0 < d - m; )
                                _ = xn(_),
                                d--;
                            for (; 0 < m - d; )
                                p = xn(p),
                                m--;
                            for (; d--; ) {
                                if (_ === p || p !== null && _ === p.alternate)
                                    break t;
                                _ = xn(_),
                                p = xn(p)
                            }
                            _ = null
                        }
                    else
                        _ = null;
                    C !== null && Vu(g, y, C, _, !1),
                    j !== null && Z !== null && Vu(g, Z, j, _, !0)
                }
            }
            e: {
                if (y = f ? En(f) : window,
                C = y.nodeName && y.nodeName.toLowerCase(),
                C === "select" || C === "input" && y.type === "file")
                    var E = Qp;
                else if (Ou(y))
                    if (wc)
                        E = Gp;
                    else {
                        E = Yp;
                        var I = Kp
                    }
                else
                    (C = y.nodeName) && C.toLowerCase() === "input" && (y.type === "checkbox" || y.type === "radio") && (E = Xp);
                if (E && (E = E(e, f))) {
                    kc(g, E, n, v);
                    break e
                }
                I && I(e, y, f),
                e === "focusout" && (I = y._wrapperState) && I.controlled && y.type === "number" && pi(y, "number", y.value)
            }
            switch (I = f ? En(f) : window,
            e) {
            case "focusin":
                (Ou(I) || I.contentEditable === "true") && (Cn = I,
                Ei = f,
                pr = null);
                break;
            case "focusout":
                pr = Ei = Cn = null;
                break;
            case "mousedown":
                zi = !0;
                break;
            case "contextmenu":
            case "mouseup":
            case "dragend":
                zi = !1,
                $u(g, n, v);
                break;
            case "selectionchange":
                if (qp)
                    break;
            case "keydown":
            case "keyup":
                $u(g, n, v)
            }
            var F;
            if (ys)
                e: {
                    switch (e) {
                    case "compositionstart":
                        var R = "onCompositionStart";
                        break e;
                    case "compositionend":
                        R = "onCompositionEnd";
                        break e;
                    case "compositionupdate":
                        R = "onCompositionUpdate";
                        break e
                    }
                    R = void 0
                }
            else
                wn ? xc(e, n) && (R = "onCompositionEnd") : e === "keydown" && n.keyCode === 229 && (R = "onCompositionStart");
            R && (vc && n.locale !== "ko" && (wn || R !== "onCompositionStart" ? R === "onCompositionEnd" && wn && (F = gc()) : (Nt = v,
            ps = "value"in Nt ? Nt.value : Nt.textContent,
            wn = !0)),
            I = Dl(f, R),
            0 < I.length && (R = new Fu(R,e,null,n,v),
            g.push({
                event: R,
                listeners: I
            }),
            F ? R.data = F : (F = Sc(n),
            F !== null && (R.data = F)))),
            (F = Bp ? $p(e, n) : Up(e, n)) && (f = Dl(f, "onBeforeInput"),
            0 < f.length && (v = new Fu("onBeforeInput","beforeinput",null,n,v),
            g.push({
                event: v,
                listeners: f
            }),
            v.data = F))
        }
        Fc(g, t)
    })
}
function _r(e, t, n) {
    return {
        instance: e,
        listener: t,
        currentTarget: n
    }
}
function Dl(e, t) {
    for (var n = t + "Capture", r = []; e !== null; ) {
        var l = e
          , o = l.stateNode;
        l.tag === 5 && o !== null && (l = o,
        o = Sr(e, n),
        o != null && r.unshift(_r(e, o, l)),
        o = Sr(e, t),
        o != null && r.push(_r(e, o, l))),
        e = e.return
    }
    return r
}
function xn(e) {
    if (e === null)
        return null;
    do
        e = e.return;
    while (e && e.tag !== 5);
    return e || null
}
function Vu(e, t, n, r, l) {
    for (var o = t._reactName, i = []; n !== null && n !== r; ) {
        var u = n
          , c = u.alternate
          , f = u.stateNode;
        if (c !== null && c === r)
            break;
        u.tag === 5 && f !== null && (u = f,
        l ? (c = Sr(n, o),
        c != null && i.unshift(_r(n, c, u))) : l || (c = Sr(n, o),
        c != null && i.push(_r(n, c, u)))),
        n = n.return
    }
    i.length !== 0 && e.push({
        event: t,
        listeners: i
    })
}
var nh = /\r\n?/g
  , rh = /\u0000|\uFFFD/g;
function Qu(e) {
    return (typeof e == "string" ? e : "" + e).replace(nh, `
`).replace(rh, "")
}
function sl(e, t, n) {
    if (t = Qu(t),
    Qu(e) !== t && n)
        throw Error(w(425))
}
function Ol() {}
var _i = null
  , Li = null;
function Ti(e, t) {
    return e === "textarea" || e === "noscript" || typeof t.children == "string" || typeof t.children == "number" || typeof t.dangerouslySetInnerHTML == "object" && t.dangerouslySetInnerHTML !== null && t.dangerouslySetInnerHTML.__html != null
}
var Pi = typeof setTimeout == "function" ? setTimeout : void 0
  , lh = typeof clearTimeout == "function" ? clearTimeout : void 0
  , Ku = typeof Promise == "function" ? Promise : void 0
  , oh = typeof queueMicrotask == "function" ? queueMicrotask : typeof Ku < "u" ? function(e) {
    return Ku.resolve(null).then(e).catch(ih)
}
: Pi;
function ih(e) {
    setTimeout(function() {
        throw e
    })
}
function Vo(e, t) {
    var n = t
      , r = 0;
    do {
        var l = n.nextSibling;
        if (e.removeChild(n),
        l && l.nodeType === 8)
            if (n = l.data,
            n === "/$") {
                if (r === 0) {
                    e.removeChild(l),
                    Cr(t);
                    return
                }
                r--
            } else
                n !== "$" && n !== "$?" && n !== "$!" || r++;
        n = l
    } while (n);
    Cr(t)
}
function Ot(e) {
    for (; e != null; e = e.nextSibling) {
        var t = e.nodeType;
        if (t === 1 || t === 3)
            break;
        if (t === 8) {
            if (t = e.data,
            t === "$" || t === "$!" || t === "$?")
                break;
            if (t === "/$")
                return null
        }
    }
    return e
}
function Yu(e) {
    e = e.previousSibling;
    for (var t = 0; e; ) {
        if (e.nodeType === 8) {
            var n = e.data;
            if (n === "$" || n === "$!" || n === "$?") {
                if (t === 0)
                    return e;
                t--
            } else
                n === "/$" && t++
        }
        e = e.previousSibling
    }
    return null
}
var Yn = Math.random().toString(36).slice(2)
  , ut = "__reactFiber$" + Yn
  , Lr = "__reactProps$" + Yn
  , xt = "__reactContainer$" + Yn
  , Ni = "__reactEvents$" + Yn
  , sh = "__reactListeners$" + Yn
  , uh = "__reactHandles$" + Yn;
function Zt(e) {
    var t = e[ut];
    if (t)
        return t;
    for (var n = e.parentNode; n; ) {
        if (t = n[xt] || n[ut]) {
            if (n = t.alternate,
            t.child !== null || n !== null && n.child !== null)
                for (e = Yu(e); e !== null; ) {
                    if (n = e[ut])
                        return n;
                    e = Yu(e)
                }
            return t
        }
        e = n,
        n = e.parentNode
    }
    return null
}
function Ar(e) {
    return e = e[ut] || e[xt],
    !e || e.tag !== 5 && e.tag !== 6 && e.tag !== 13 && e.tag !== 3 ? null : e
}
function En(e) {
    if (e.tag === 5 || e.tag === 6)
        return e.stateNode;
    throw Error(w(33))
}
function ro(e) {
    return e[Lr] || null
}
var Fi = []
  , zn = -1;
function Vt(e) {
    return {
        current: e
    }
}
function ee(e) {
    0 > zn || (e.current = Fi[zn],
    Fi[zn] = null,
    zn--)
}
function q(e, t) {
    zn++,
    Fi[zn] = e.current,
    e.current = t
}
var Ut = {}
  , Ce = Vt(Ut)
  , Re = Vt(!1)
  , rn = Ut;
function Wn(e, t) {
    var n = e.type.contextTypes;
    if (!n)
        return Ut;
    var r = e.stateNode;
    if (r && r.__reactInternalMemoizedUnmaskedChildContext === t)
        return r.__reactInternalMemoizedMaskedChildContext;
    var l = {}, o;
    for (o in n)
        l[o] = t[o];
    return r && (e = e.stateNode,
    e.__reactInternalMemoizedUnmaskedChildContext = t,
    e.__reactInternalMemoizedMaskedChildContext = l),
    l
}
function De(e) {
    return e = e.childContextTypes,
    e != null
}
function Ml() {
    ee(Re),
    ee(Ce)
}
function Xu(e, t, n) {
    if (Ce.current !== Ut)
        throw Error(w(168));
    q(Ce, t),
    q(Re, n)
}
function Rc(e, t, n) {
    var r = e.stateNode;
    if (t = t.childContextTypes,
    typeof r.getChildContext != "function")
        return n;
    r = r.getChildContext();
    for (var l in r)
        if (!(l in t))
            throw Error(w(108, Kf(e) || "Unknown", l));
    return se({}, n, r)
}
function Al(e) {
    return e = (e = e.stateNode) && e.__reactInternalMemoizedMergedChildContext || Ut,
    rn = Ce.current,
    q(Ce, e),
    q(Re, Re.current),
    !0
}
function Gu(e, t, n) {
    var r = e.stateNode;
    if (!r)
        throw Error(w(169));
    n ? (e = Rc(e, t, rn),
    r.__reactInternalMemoizedMergedChildContext = e,
    ee(Re),
    ee(Ce),
    q(Ce, e)) : ee(Re),
    q(Re, n)
}
var ht = null
  , lo = !1
  , Qo = !1;
function Dc(e) {
    ht === null ? ht = [e] : ht.push(e)
}
function ah(e) {
    lo = !0,
    Dc(e)
}
function Qt() {
    if (!Qo && ht !== null) {
        Qo = !0;
        var e = 0
          , t = G;
        try {
            var n = ht;
            for (G = 1; e < n.length; e++) {
                var r = n[e];
                do
                    r = r(!0);
                while (r !== null)
            }
            ht = null,
            lo = !1
        } catch (l) {
            throw ht !== null && (ht = ht.slice(e + 1)),
            ic(as, Qt),
            l
        } finally {
            G = t,
            Qo = !1
        }
    }
    return null
}
var _n = []
  , Ln = 0
  , Wl = null
  , Bl = 0
  , Ve = []
  , Qe = 0
  , ln = null
  , mt = 1
  , yt = "";
function Gt(e, t) {
    _n[Ln++] = Bl,
    _n[Ln++] = Wl,
    Wl = e,
    Bl = t
}
function Oc(e, t, n) {
    Ve[Qe++] = mt,
    Ve[Qe++] = yt,
    Ve[Qe++] = ln,
    ln = e;
    var r = mt;
    e = yt;
    var l = 32 - et(r) - 1;
    r &= ~(1 << l),
    n += 1;
    var o = 32 - et(t) + l;
    if (30 < o) {
        var i = l - l % 5;
        o = (r & (1 << i) - 1).toString(32),
        r >>= i,
        l -= i,
        mt = 1 << 32 - et(t) + l | n << l | r,
        yt = o + e
    } else
        mt = 1 << o | n << l | r,
        yt = e
}
function vs(e) {
    e.return !== null && (Gt(e, 1),
    Oc(e, 1, 0))
}
function xs(e) {
    for (; e === Wl; )
        Wl = _n[--Ln],
        _n[Ln] = null,
        Bl = _n[--Ln],
        _n[Ln] = null;
    for (; e === ln; )
        ln = Ve[--Qe],
        Ve[Qe] = null,
        yt = Ve[--Qe],
        Ve[Qe] = null,
        mt = Ve[--Qe],
        Ve[Qe] = null
}
var We = null
  , Ae = null
  , le = !1
  , be = null;
function Mc(e, t) {
    var n = Ke(5, null, null, 0);
    n.elementType = "DELETED",
    n.stateNode = t,
    n.return = e,
    t = e.deletions,
    t === null ? (e.deletions = [n],
    e.flags |= 16) : t.push(n)
}
function Ju(e, t) {
    switch (e.tag) {
    case 5:
        var n = e.type;
        return t = t.nodeType !== 1 || n.toLowerCase() !== t.nodeName.toLowerCase() ? null : t,
        t !== null ? (e.stateNode = t,
        We = e,
        Ae = Ot(t.firstChild),
        !0) : !1;
    case 6:
        return t = e.pendingProps === "" || t.nodeType !== 3 ? null : t,
        t !== null ? (e.stateNode = t,
        We = e,
        Ae = null,
        !0) : !1;
    case 13:
        return t = t.nodeType !== 8 ? null : t,
        t !== null ? (n = ln !== null ? {
            id: mt,
            overflow: yt
        } : null,
        e.memoizedState = {
            dehydrated: t,
            treeContext: n,
            retryLane: 1073741824
        },
        n = Ke(18, null, null, 0),
        n.stateNode = t,
        n.return = e,
        e.child = n,
        We = e,
        Ae = null,
        !0) : !1;
    default:
        return !1
    }
}
function Ii(e) {
    return (e.mode & 1) !== 0 && (e.flags & 128) === 0
}
function Ri(e) {
    if (le) {
        var t = Ae;
        if (t) {
            var n = t;
            if (!Ju(e, t)) {
                if (Ii(e))
                    throw Error(w(418));
                t = Ot(n.nextSibling);
                var r = We;
                t && Ju(e, t) ? Mc(r, n) : (e.flags = e.flags & -4097 | 2,
                le = !1,
                We = e)
            }
        } else {
            if (Ii(e))
                throw Error(w(418));
            e.flags = e.flags & -4097 | 2,
            le = !1,
            We = e
        }
    }
}
function Zu(e) {
    for (e = e.return; e !== null && e.tag !== 5 && e.tag !== 3 && e.tag !== 13; )
        e = e.return;
    We = e
}
function ul(e) {
    if (e !== We)
        return !1;
    if (!le)
        return Zu(e),
        le = !0,
        !1;
    var t;
    if ((t = e.tag !== 3) && !(t = e.tag !== 5) && (t = e.type,
    t = t !== "head" && t !== "body" && !Ti(e.type, e.memoizedProps)),
    t && (t = Ae)) {
        if (Ii(e))
            throw Ac(),
            Error(w(418));
        for (; t; )
            Mc(e, t),
            t = Ot(t.nextSibling)
    }
    if (Zu(e),
    e.tag === 13) {
        if (e = e.memoizedState,
        e = e !== null ? e.dehydrated : null,
        !e)
            throw Error(w(317));
        e: {
            for (e = e.nextSibling,
            t = 0; e; ) {
                if (e.nodeType === 8) {
                    var n = e.data;
                    if (n === "/$") {
                        if (t === 0) {
                            Ae = Ot(e.nextSibling);
                            break e
                        }
                        t--
                    } else
                        n !== "$" && n !== "$!" && n !== "$?" || t++
                }
                e = e.nextSibling
            }
            Ae = null
        }
    } else
        Ae = We ? Ot(e.stateNode.nextSibling) : null;
    return !0
}
function Ac() {
    for (var e = Ae; e; )
        e = Ot(e.nextSibling)
}
function Bn() {
    Ae = We = null,
    le = !1
}
function Ss(e) {
    be === null ? be = [e] : be.push(e)
}
var ch = wt.ReactCurrentBatchConfig;
function tr(e, t, n) {
    if (e = n.ref,
    e !== null && typeof e != "function" && typeof e != "object") {
        if (n._owner) {
            if (n = n._owner,
            n) {
                if (n.tag !== 1)
                    throw Error(w(309));
                var r = n.stateNode
            }
            if (!r)
                throw Error(w(147, e));
            var l = r
              , o = "" + e;
            return t !== null && t.ref !== null && typeof t.ref == "function" && t.ref._stringRef === o ? t.ref : (t = function(i) {
                var u = l.refs;
                i === null ? delete u[o] : u[o] = i
            }
            ,
            t._stringRef = o,
            t)
        }
        if (typeof e != "string")
            throw Error(w(284));
        if (!n._owner)
            throw Error(w(290, e))
    }
    return e
}
function al(e, t) {
    throw e = Object.prototype.toString.call(t),
    Error(w(31, e === "[object Object]" ? "object with keys {" + Object.keys(t).join(", ") + "}" : e))
}
function qu(e) {
    var t = e._init;
    return t(e._payload)
}
function Wc(e) {
    function t(p, d) {
        if (e) {
            var m = p.deletions;
            m === null ? (p.deletions = [d],
            p.flags |= 16) : m.push(d)
        }
    }
    function n(p, d) {
        if (!e)
            return null;
        for (; d !== null; )
            t(p, d),
            d = d.sibling;
        return null
    }
    function r(p, d) {
        for (p = new Map; d !== null; )
            d.key !== null ? p.set(d.key, d) : p.set(d.index, d),
            d = d.sibling;
        return p
    }
    function l(p, d) {
        return p = Bt(p, d),
        p.index = 0,
        p.sibling = null,
        p
    }
    function o(p, d, m) {
        return p.index = m,
        e ? (m = p.alternate,
        m !== null ? (m = m.index,
        m < d ? (p.flags |= 2,
        d) : m) : (p.flags |= 2,
        d)) : (p.flags |= 1048576,
        d)
    }
    function i(p) {
        return e && p.alternate === null && (p.flags |= 2),
        p
    }
    function u(p, d, m, S) {
        return d === null || d.tag !== 6 ? (d = qo(m, p.mode, S),
        d.return = p,
        d) : (d = l(d, m),
        d.return = p,
        d)
    }
    function c(p, d, m, S) {
        var E = m.type;
        return E === kn ? v(p, d, m.props.children, S, m.key) : d !== null && (d.elementType === E || typeof E == "object" && E !== null && E.$$typeof === _t && qu(E) === d.type) ? (S = l(d, m.props),
        S.ref = tr(p, d, m),
        S.return = p,
        S) : (S = _l(m.type, m.key, m.props, null, p.mode, S),
        S.ref = tr(p, d, m),
        S.return = p,
        S)
    }
    function f(p, d, m, S) {
        return d === null || d.tag !== 4 || d.stateNode.containerInfo !== m.containerInfo || d.stateNode.implementation !== m.implementation ? (d = bo(m, p.mode, S),
        d.return = p,
        d) : (d = l(d, m.children || []),
        d.return = p,
        d)
    }
    function v(p, d, m, S, E) {
        return d === null || d.tag !== 7 ? (d = tn(m, p.mode, S, E),
        d.return = p,
        d) : (d = l(d, m),
        d.return = p,
        d)
    }
    function g(p, d, m) {
        if (typeof d == "string" && d !== "" || typeof d == "number")
            return d = qo("" + d, p.mode, m),
            d.return = p,
            d;
        if (typeof d == "object" && d !== null) {
            switch (d.$$typeof) {
            case qr:
                return m = _l(d.type, d.key, d.props, null, p.mode, m),
                m.ref = tr(p, null, d),
                m.return = p,
                m;
            case Sn:
                return d = bo(d, p.mode, m),
                d.return = p,
                d;
            case _t:
                var S = d._init;
                return g(p, S(d._payload), m)
            }
            if (ir(d) || Jn(d))
                return d = tn(d, p.mode, m, null),
                d.return = p,
                d;
            al(p, d)
        }
        return null
    }
    function y(p, d, m, S) {
        var E = d !== null ? d.key : null;
        if (typeof m == "string" && m !== "" || typeof m == "number")
            return E !== null ? null : u(p, d, "" + m, S);
        if (typeof m == "object" && m !== null) {
            switch (m.$$typeof) {
            case qr:
                return m.key === E ? c(p, d, m, S) : null;
            case Sn:
                return m.key === E ? f(p, d, m, S) : null;
            case _t:
                return E = m._init,
                y(p, d, E(m._payload), S)
            }
            if (ir(m) || Jn(m))
                return E !== null ? null : v(p, d, m, S, null);
            al(p, m)
        }
        return null
    }
    function C(p, d, m, S, E) {
        if (typeof S == "string" && S !== "" || typeof S == "number")
            return p = p.get(m) || null,
            u(d, p, "" + S, E);
        if (typeof S == "object" && S !== null) {
            switch (S.$$typeof) {
            case qr:
                return p = p.get(S.key === null ? m : S.key) || null,
                c(d, p, S, E);
            case Sn:
                return p = p.get(S.key === null ? m : S.key) || null,
                f(d, p, S, E);
            case _t:
                var I = S._init;
                return C(p, d, m, I(S._payload), E)
            }
            if (ir(S) || Jn(S))
                return p = p.get(m) || null,
                v(d, p, S, E, null);
            al(d, S)
        }
        return null
    }
    function j(p, d, m, S) {
        for (var E = null, I = null, F = d, R = d = 0, te = null; F !== null && R < m.length; R++) {
            F.index > R ? (te = F,
            F = null) : te = F.sibling;
            var $ = y(p, F, m[R], S);
            if ($ === null) {
                F === null && (F = te);
                break
            }
            e && F && $.alternate === null && t(p, F),
            d = o($, d, R),
            I === null ? E = $ : I.sibling = $,
            I = $,
            F = te
        }
        if (R === m.length)
            return n(p, F),
            le && Gt(p, R),
            E;
        if (F === null) {
            for (; R < m.length; R++)
                F = g(p, m[R], S),
                F !== null && (d = o(F, d, R),
                I === null ? E = F : I.sibling = F,
                I = F);
            return le && Gt(p, R),
            E
        }
        for (F = r(p, F); R < m.length; R++)
            te = C(F, p, R, m[R], S),
            te !== null && (e && te.alternate !== null && F.delete(te.key === null ? R : te.key),
            d = o(te, d, R),
            I === null ? E = te : I.sibling = te,
            I = te);
        return e && F.forEach(function(Pe) {
            return t(p, Pe)
        }),
        le && Gt(p, R),
        E
    }
    function _(p, d, m, S) {
        var E = Jn(m);
        if (typeof E != "function")
            throw Error(w(150));
        if (m = E.call(m),
        m == null)
            throw Error(w(151));
        for (var I = E = null, F = d, R = d = 0, te = null, $ = m.next(); F !== null && !$.done; R++,
        $ = m.next()) {
            F.index > R ? (te = F,
            F = null) : te = F.sibling;
            var Pe = y(p, F, $.value, S);
            if (Pe === null) {
                F === null && (F = te);
                break
            }
            e && F && Pe.alternate === null && t(p, F),
            d = o(Pe, d, R),
            I === null ? E = Pe : I.sibling = Pe,
            I = Pe,
            F = te
        }
        if ($.done)
            return n(p, F),
            le && Gt(p, R),
            E;
        if (F === null) {
            for (; !$.done; R++,
            $ = m.next())
                $ = g(p, $.value, S),
                $ !== null && (d = o($, d, R),
                I === null ? E = $ : I.sibling = $,
                I = $);
            return le && Gt(p, R),
            E
        }
        for (F = r(p, F); !$.done; R++,
        $ = m.next())
            $ = C(F, p, R, $.value, S),
            $ !== null && (e && $.alternate !== null && F.delete($.key === null ? R : $.key),
            d = o($, d, R),
            I === null ? E = $ : I.sibling = $,
            I = $);
        return e && F.forEach(function(Ct) {
            return t(p, Ct)
        }),
        le && Gt(p, R),
        E
    }
    function Z(p, d, m, S) {
        if (typeof m == "object" && m !== null && m.type === kn && m.key === null && (m = m.props.children),
        typeof m == "object" && m !== null) {
            switch (m.$$typeof) {
            case qr:
                e: {
                    for (var E = m.key, I = d; I !== null; ) {
                        if (I.key === E) {
                            if (E = m.type,
                            E === kn) {
                                if (I.tag === 7) {
                                    n(p, I.sibling),
                                    d = l(I, m.props.children),
                                    d.return = p,
                                    p = d;
                                    break e
                                }
                            } else if (I.elementType === E || typeof E == "object" && E !== null && E.$$typeof === _t && qu(E) === I.type) {
                                n(p, I.sibling),
                                d = l(I, m.props),
                                d.ref = tr(p, I, m),
                                d.return = p,
                                p = d;
                                break e
                            }
                            n(p, I);
                            break
                        } else
                            t(p, I);
                        I = I.sibling
                    }
                    m.type === kn ? (d = tn(m.props.children, p.mode, S, m.key),
                    d.return = p,
                    p = d) : (S = _l(m.type, m.key, m.props, null, p.mode, S),
                    S.ref = tr(p, d, m),
                    S.return = p,
                    p = S)
                }
                return i(p);
            case Sn:
                e: {
                    for (I = m.key; d !== null; ) {
                        if (d.key === I)
                            if (d.tag === 4 && d.stateNode.containerInfo === m.containerInfo && d.stateNode.implementation === m.implementation) {
                                n(p, d.sibling),
                                d = l(d, m.children || []),
                                d.return = p,
                                p = d;
                                break e
                            } else {
                                n(p, d);
                                break
                            }
                        else
                            t(p, d);
                        d = d.sibling
                    }
                    d = bo(m, p.mode, S),
                    d.return = p,
                    p = d
                }
                return i(p);
            case _t:
                return I = m._init,
                Z(p, d, I(m._payload), S)
            }
            if (ir(m))
                return j(p, d, m, S);
            if (Jn(m))
                return _(p, d, m, S);
            al(p, m)
        }
        return typeof m == "string" && m !== "" || typeof m == "number" ? (m = "" + m,
        d !== null && d.tag === 6 ? (n(p, d.sibling),
        d = l(d, m),
        d.return = p,
        p = d) : (n(p, d),
        d = qo(m, p.mode, S),
        d.return = p,
        p = d),
        i(p)) : n(p, d)
    }
    return Z
}
var $n = Wc(!0)
  , Bc = Wc(!1)
  , $l = Vt(null)
  , Ul = null
  , Tn = null
  , ks = null;
function ws() {
    ks = Tn = Ul = null
}
function Cs(e) {
    var t = $l.current;
    ee($l),
    e._currentValue = t
}
function Di(e, t, n) {
    for (; e !== null; ) {
        var r = e.alternate;
        if ((e.childLanes & t) !== t ? (e.childLanes |= t,
        r !== null && (r.childLanes |= t)) : r !== null && (r.childLanes & t) !== t && (r.childLanes |= t),
        e === n)
            break;
        e = e.return
    }
}
function On(e, t) {
    Ul = e,
    ks = Tn = null,
    e = e.dependencies,
    e !== null && e.firstContext !== null && (e.lanes & t && (Ie = !0),
    e.firstContext = null)
}
function Xe(e) {
    var t = e._currentValue;
    if (ks !== e)
        if (e = {
            context: e,
            memoizedValue: t,
            next: null
        },
        Tn === null) {
            if (Ul === null)
                throw Error(w(308));
            Tn = e,
            Ul.dependencies = {
                lanes: 0,
                firstContext: e
            }
        } else
            Tn = Tn.next = e;
    return t
}
var qt = null;
function js(e) {
    qt === null ? qt = [e] : qt.push(e)
}
function $c(e, t, n, r) {
    var l = t.interleaved;
    return l === null ? (n.next = n,
    js(t)) : (n.next = l.next,
    l.next = n),
    t.interleaved = n,
    St(e, r)
}
function St(e, t) {
    e.lanes |= t;
    var n = e.alternate;
    for (n !== null && (n.lanes |= t),
    n = e,
    e = e.return; e !== null; )
        e.childLanes |= t,
        n = e.alternate,
        n !== null && (n.childLanes |= t),
        n = e,
        e = e.return;
    return n.tag === 3 ? n.stateNode : null
}
var Lt = !1;
function Es(e) {
    e.updateQueue = {
        baseState: e.memoizedState,
        firstBaseUpdate: null,
        lastBaseUpdate: null,
        shared: {
            pending: null,
            interleaved: null,
            lanes: 0
        },
        effects: null
    }
}
function Uc(e, t) {
    e = e.updateQueue,
    t.updateQueue === e && (t.updateQueue = {
        baseState: e.baseState,
        firstBaseUpdate: e.firstBaseUpdate,
        lastBaseUpdate: e.lastBaseUpdate,
        shared: e.shared,
        effects: e.effects
    })
}
function gt(e, t) {
    return {
        eventTime: e,
        lane: t,
        tag: 0,
        payload: null,
        callback: null,
        next: null
    }
}
function Mt(e, t, n) {
    var r = e.updateQueue;
    if (r === null)
        return null;
    if (r = r.shared,
    Y & 2) {
        var l = r.pending;
        return l === null ? t.next = t : (t.next = l.next,
        l.next = t),
        r.pending = t,
        St(e, n)
    }
    return l = r.interleaved,
    l === null ? (t.next = t,
    js(r)) : (t.next = l.next,
    l.next = t),
    r.interleaved = t,
    St(e, n)
}
function kl(e, t, n) {
    if (t = t.updateQueue,
    t !== null && (t = t.shared,
    (n & 4194240) !== 0)) {
        var r = t.lanes;
        r &= e.pendingLanes,
        n |= r,
        t.lanes = n,
        cs(e, n)
    }
}
function bu(e, t) {
    var n = e.updateQueue
      , r = e.alternate;
    if (r !== null && (r = r.updateQueue,
    n === r)) {
        var l = null
          , o = null;
        if (n = n.firstBaseUpdate,
        n !== null) {
            do {
                var i = {
                    eventTime: n.eventTime,
                    lane: n.lane,
                    tag: n.tag,
                    payload: n.payload,
                    callback: n.callback,
                    next: null
                };
                o === null ? l = o = i : o = o.next = i,
                n = n.next
            } while (n !== null);
            o === null ? l = o = t : o = o.next = t
        } else
            l = o = t;
        n = {
            baseState: r.baseState,
            firstBaseUpdate: l,
            lastBaseUpdate: o,
            shared: r.shared,
            effects: r.effects
        },
        e.updateQueue = n;
        return
    }
    e = n.lastBaseUpdate,
    e === null ? n.firstBaseUpdate = t : e.next = t,
    n.lastBaseUpdate = t
}
function Hl(e, t, n, r) {
    var l = e.updateQueue;
    Lt = !1;
    var o = l.firstBaseUpdate
      , i = l.lastBaseUpdate
      , u = l.shared.pending;
    if (u !== null) {
        l.shared.pending = null;
        var c = u
          , f = c.next;
        c.next = null,
        i === null ? o = f : i.next = f,
        i = c;
        var v = e.alternate;
        v !== null && (v = v.updateQueue,
        u = v.lastBaseUpdate,
        u !== i && (u === null ? v.firstBaseUpdate = f : u.next = f,
        v.lastBaseUpdate = c))
    }
    if (o !== null) {
        var g = l.baseState;
        i = 0,
        v = f = c = null,
        u = o;
        do {
            var y = u.lane
              , C = u.eventTime;
            if ((r & y) === y) {
                v !== null && (v = v.next = {
                    eventTime: C,
                    lane: 0,
                    tag: u.tag,
                    payload: u.payload,
                    callback: u.callback,
                    next: null
                });
                e: {
                    var j = e
                      , _ = u;
                    switch (y = t,
                    C = n,
                    _.tag) {
                    case 1:
                        if (j = _.payload,
                        typeof j == "function") {
                            g = j.call(C, g, y);
                            break e
                        }
                        g = j;
                        break e;
                    case 3:
                        j.flags = j.flags & -65537 | 128;
                    case 0:
                        if (j = _.payload,
                        y = typeof j == "function" ? j.call(C, g, y) : j,
                        y == null)
                            break e;
                        g = se({}, g, y);
                        break e;
                    case 2:
                        Lt = !0
                    }
                }
                u.callback !== null && u.lane !== 0 && (e.flags |= 64,
                y = l.effects,
                y === null ? l.effects = [u] : y.push(u))
            } else
                C = {
                    eventTime: C,
                    lane: y,
                    tag: u.tag,
                    payload: u.payload,
                    callback: u.callback,
                    next: null
                },
                v === null ? (f = v = C,
                c = g) : v = v.next = C,
                i |= y;
            if (u = u.next,
            u === null) {
                if (u = l.shared.pending,
                u === null)
                    break;
                y = u,
                u = y.next,
                y.next = null,
                l.lastBaseUpdate = y,
                l.shared.pending = null
            }
        } while (!0);
        if (v === null && (c = g),
        l.baseState = c,
        l.firstBaseUpdate = f,
        l.lastBaseUpdate = v,
        t = l.shared.interleaved,
        t !== null) {
            l = t;
            do
                i |= l.lane,
                l = l.next;
            while (l !== t)
        } else
            o === null && (l.shared.lanes = 0);
        sn |= i,
        e.lanes = i,
        e.memoizedState = g
    }
}
function ea(e, t, n) {
    if (e = t.effects,
    t.effects = null,
    e !== null)
        for (t = 0; t < e.length; t++) {
            var r = e[t]
              , l = r.callback;
            if (l !== null) {
                if (r.callback = null,
                r = n,
                typeof l != "function")
                    throw Error(w(191, l));
                l.call(r)
            }
        }
}
var Wr = {}
  , ct = Vt(Wr)
  , Tr = Vt(Wr)
  , Pr = Vt(Wr);
function bt(e) {
    if (e === Wr)
        throw Error(w(174));
    return e
}
function zs(e, t) {
    switch (q(Pr, t),
    q(Tr, e),
    q(ct, Wr),
    e = t.nodeType,
    e) {
    case 9:
    case 11:
        t = (t = t.documentElement) ? t.namespaceURI : mi(null, "");
        break;
    default:
        e = e === 8 ? t.parentNode : t,
        t = e.namespaceURI || null,
        e = e.tagName,
        t = mi(t, e)
    }
    ee(ct),
    q(ct, t)
}
function Un() {
    ee(ct),
    ee(Tr),
    ee(Pr)
}
function Hc(e) {
    bt(Pr.current);
    var t = bt(ct.current)
      , n = mi(t, e.type);
    t !== n && (q(Tr, e),
    q(ct, n))
}
function _s(e) {
    Tr.current === e && (ee(ct),
    ee(Tr))
}
var oe = Vt(0);
function Vl(e) {
    for (var t = e; t !== null; ) {
        if (t.tag === 13) {
            var n = t.memoizedState;
            if (n !== null && (n = n.dehydrated,
            n === null || n.data === "$?" || n.data === "$!"))
                return t
        } else if (t.tag === 19 && t.memoizedProps.revealOrder !== void 0) {
            if (t.flags & 128)
                return t
        } else if (t.child !== null) {
            t.child.return = t,
            t = t.child;
            continue
        }
        if (t === e)
            break;
        for (; t.sibling === null; ) {
            if (t.return === null || t.return === e)
                return null;
            t = t.return
        }
        t.sibling.return = t.return,
        t = t.sibling
    }
    return null
}
var Ko = [];
function Ls() {
    for (var e = 0; e < Ko.length; e++)
        Ko[e]._workInProgressVersionPrimary = null;
    Ko.length = 0
}
var wl = wt.ReactCurrentDispatcher
  , Yo = wt.ReactCurrentBatchConfig
  , on = 0
  , ie = null
  , fe = null
  , he = null
  , Ql = !1
  , hr = !1
  , Nr = 0
  , dh = 0;
function Se() {
    throw Error(w(321))
}
function Ts(e, t) {
    if (t === null)
        return !1;
    for (var n = 0; n < t.length && n < e.length; n++)
        if (!nt(e[n], t[n]))
            return !1;
    return !0
}
function Ps(e, t, n, r, l, o) {
    if (on = o,
    ie = t,
    t.memoizedState = null,
    t.updateQueue = null,
    t.lanes = 0,
    wl.current = e === null || e.memoizedState === null ? mh : yh,
    e = n(r, l),
    hr) {
        o = 0;
        do {
            if (hr = !1,
            Nr = 0,
            25 <= o)
                throw Error(w(301));
            o += 1,
            he = fe = null,
            t.updateQueue = null,
            wl.current = gh,
            e = n(r, l)
        } while (hr)
    }
    if (wl.current = Kl,
    t = fe !== null && fe.next !== null,
    on = 0,
    he = fe = ie = null,
    Ql = !1,
    t)
        throw Error(w(300));
    return e
}
function Ns() {
    var e = Nr !== 0;
    return Nr = 0,
    e
}
function st() {
    var e = {
        memoizedState: null,
        baseState: null,
        baseQueue: null,
        queue: null,
        next: null
    };
    return he === null ? ie.memoizedState = he = e : he = he.next = e,
    he
}
function Ge() {
    if (fe === null) {
        var e = ie.alternate;
        e = e !== null ? e.memoizedState : null
    } else
        e = fe.next;
    var t = he === null ? ie.memoizedState : he.next;
    if (t !== null)
        he = t,
        fe = e;
    else {
        if (e === null)
            throw Error(w(310));
        fe = e,
        e = {
            memoizedState: fe.memoizedState,
            baseState: fe.baseState,
            baseQueue: fe.baseQueue,
            queue: fe.queue,
            next: null
        },
        he === null ? ie.memoizedState = he = e : he = he.next = e
    }
    return he
}
function Fr(e, t) {
    return typeof t == "function" ? t(e) : t
}
function Xo(e) {
    var t = Ge()
      , n = t.queue;
    if (n === null)
        throw Error(w(311));
    n.lastRenderedReducer = e;
    var r = fe
      , l = r.baseQueue
      , o = n.pending;
    if (o !== null) {
        if (l !== null) {
            var i = l.next;
            l.next = o.next,
            o.next = i
        }
        r.baseQueue = l = o,
        n.pending = null
    }
    if (l !== null) {
        o = l.next,
        r = r.baseState;
        var u = i = null
          , c = null
          , f = o;
        do {
            var v = f.lane;
            if ((on & v) === v)
                c !== null && (c = c.next = {
                    lane: 0,
                    action: f.action,
                    hasEagerState: f.hasEagerState,
                    eagerState: f.eagerState,
                    next: null
                }),
                r = f.hasEagerState ? f.eagerState : e(r, f.action);
            else {
                var g = {
                    lane: v,
                    action: f.action,
                    hasEagerState: f.hasEagerState,
                    eagerState: f.eagerState,
                    next: null
                };
                c === null ? (u = c = g,
                i = r) : c = c.next = g,
                ie.lanes |= v,
                sn |= v
            }
            f = f.next
        } while (f !== null && f !== o);
        c === null ? i = r : c.next = u,
        nt(r, t.memoizedState) || (Ie = !0),
        t.memoizedState = r,
        t.baseState = i,
        t.baseQueue = c,
        n.lastRenderedState = r
    }
    if (e = n.interleaved,
    e !== null) {
        l = e;
        do
            o = l.lane,
            ie.lanes |= o,
            sn |= o,
            l = l.next;
        while (l !== e)
    } else
        l === null && (n.lanes = 0);
    return [t.memoizedState, n.dispatch]
}
function Go(e) {
    var t = Ge()
      , n = t.queue;
    if (n === null)
        throw Error(w(311));
    n.lastRenderedReducer = e;
    var r = n.dispatch
      , l = n.pending
      , o = t.memoizedState;
    if (l !== null) {
        n.pending = null;
        var i = l = l.next;
        do
            o = e(o, i.action),
            i = i.next;
        while (i !== l);
        nt(o, t.memoizedState) || (Ie = !0),
        t.memoizedState = o,
        t.baseQueue === null && (t.baseState = o),
        n.lastRenderedState = o
    }
    return [o, r]
}
function Vc() {}
function Qc(e, t) {
    var n = ie
      , r = Ge()
      , l = t()
      , o = !nt(r.memoizedState, l);
    if (o && (r.memoizedState = l,
    Ie = !0),
    r = r.queue,
    Fs(Xc.bind(null, n, r, e), [e]),
    r.getSnapshot !== t || o || he !== null && he.memoizedState.tag & 1) {
        if (n.flags |= 2048,
        Ir(9, Yc.bind(null, n, r, l, t), void 0, null),
        me === null)
            throw Error(w(349));
        on & 30 || Kc(n, t, l)
    }
    return l
}
function Kc(e, t, n) {
    e.flags |= 16384,
    e = {
        getSnapshot: t,
        value: n
    },
    t = ie.updateQueue,
    t === null ? (t = {
        lastEffect: null,
        stores: null
    },
    ie.updateQueue = t,
    t.stores = [e]) : (n = t.stores,
    n === null ? t.stores = [e] : n.push(e))
}
function Yc(e, t, n, r) {
    t.value = n,
    t.getSnapshot = r,
    Gc(t) && Jc(e)
}
function Xc(e, t, n) {
    return n(function() {
        Gc(t) && Jc(e)
    })
}
function Gc(e) {
    var t = e.getSnapshot;
    e = e.value;
    try {
        var n = t();
        return !nt(e, n)
    } catch {
        return !0
    }
}
function Jc(e) {
    var t = St(e, 1);
    t !== null && tt(t, e, 1, -1)
}
function ta(e) {
    var t = st();
    return typeof e == "function" && (e = e()),
    t.memoizedState = t.baseState = e,
    e = {
        pending: null,
        interleaved: null,
        lanes: 0,
        dispatch: null,
        lastRenderedReducer: Fr,
        lastRenderedState: e
    },
    t.queue = e,
    e = e.dispatch = hh.bind(null, ie, e),
    [t.memoizedState, e]
}
function Ir(e, t, n, r) {
    return e = {
        tag: e,
        create: t,
        destroy: n,
        deps: r,
        next: null
    },
    t = ie.updateQueue,
    t === null ? (t = {
        lastEffect: null,
        stores: null
    },
    ie.updateQueue = t,
    t.lastEffect = e.next = e) : (n = t.lastEffect,
    n === null ? t.lastEffect = e.next = e : (r = n.next,
    n.next = e,
    e.next = r,
    t.lastEffect = e)),
    e
}
function Zc() {
    return Ge().memoizedState
}
function Cl(e, t, n, r) {
    var l = st();
    ie.flags |= e,
    l.memoizedState = Ir(1 | t, n, void 0, r === void 0 ? null : r)
}
function oo(e, t, n, r) {
    var l = Ge();
    r = r === void 0 ? null : r;
    var o = void 0;
    if (fe !== null) {
        var i = fe.memoizedState;
        if (o = i.destroy,
        r !== null && Ts(r, i.deps)) {
            l.memoizedState = Ir(t, n, o, r);
            return
        }
    }
    ie.flags |= e,
    l.memoizedState = Ir(1 | t, n, o, r)
}
function na(e, t) {
    return Cl(8390656, 8, e, t)
}
function Fs(e, t) {
    return oo(2048, 8, e, t)
}
function qc(e, t) {
    return oo(4, 2, e, t)
}
function bc(e, t) {
    return oo(4, 4, e, t)
}
function ed(e, t) {
    if (typeof t == "function")
        return e = e(),
        t(e),
        function() {
            t(null)
        }
        ;
    if (t != null)
        return e = e(),
        t.current = e,
        function() {
            t.current = null
        }
}
function td(e, t, n) {
    return n = n != null ? n.concat([e]) : null,
    oo(4, 4, ed.bind(null, t, e), n)
}
function Is() {}
function nd(e, t) {
    var n = Ge();
    t = t === void 0 ? null : t;
    var r = n.memoizedState;
    return r !== null && t !== null && Ts(t, r[1]) ? r[0] : (n.memoizedState = [e, t],
    e)
}
function rd(e, t) {
    var n = Ge();
    t = t === void 0 ? null : t;
    var r = n.memoizedState;
    return r !== null && t !== null && Ts(t, r[1]) ? r[0] : (e = e(),
    n.memoizedState = [e, t],
    e)
}
function ld(e, t, n) {
    return on & 21 ? (nt(n, t) || (n = ac(),
    ie.lanes |= n,
    sn |= n,
    e.baseState = !0),
    t) : (e.baseState && (e.baseState = !1,
    Ie = !0),
    e.memoizedState = n)
}
function fh(e, t) {
    var n = G;
    G = n !== 0 && 4 > n ? n : 4,
    e(!0);
    var r = Yo.transition;
    Yo.transition = {};
    try {
        e(!1),
        t()
    } finally {
        G = n,
        Yo.transition = r
    }
}
function od() {
    return Ge().memoizedState
}
function ph(e, t, n) {
    var r = Wt(e);
    if (n = {
        lane: r,
        action: n,
        hasEagerState: !1,
        eagerState: null,
        next: null
    },
    id(e))
        sd(t, n);
    else if (n = $c(e, t, n, r),
    n !== null) {
        var l = _e();
        tt(n, e, r, l),
        ud(n, t, r)
    }
}
function hh(e, t, n) {
    var r = Wt(e)
      , l = {
        lane: r,
        action: n,
        hasEagerState: !1,
        eagerState: null,
        next: null
    };
    if (id(e))
        sd(t, l);
    else {
        var o = e.alternate;
        if (e.lanes === 0 && (o === null || o.lanes === 0) && (o = t.lastRenderedReducer,
        o !== null))
            try {
                var i = t.lastRenderedState
                  , u = o(i, n);
                if (l.hasEagerState = !0,
                l.eagerState = u,
                nt(u, i)) {
                    var c = t.interleaved;
                    c === null ? (l.next = l,
                    js(t)) : (l.next = c.next,
                    c.next = l),
                    t.interleaved = l;
                    return
                }
            } catch {} finally {}
        n = $c(e, t, l, r),
        n !== null && (l = _e(),
        tt(n, e, r, l),
        ud(n, t, r))
    }
}
function id(e) {
    var t = e.alternate;
    return e === ie || t !== null && t === ie
}
function sd(e, t) {
    hr = Ql = !0;
    var n = e.pending;
    n === null ? t.next = t : (t.next = n.next,
    n.next = t),
    e.pending = t
}
function ud(e, t, n) {
    if (n & 4194240) {
        var r = t.lanes;
        r &= e.pendingLanes,
        n |= r,
        t.lanes = n,
        cs(e, n)
    }
}
var Kl = {
    readContext: Xe,
    useCallback: Se,
    useContext: Se,
    useEffect: Se,
    useImperativeHandle: Se,
    useInsertionEffect: Se,
    useLayoutEffect: Se,
    useMemo: Se,
    useReducer: Se,
    useRef: Se,
    useState: Se,
    useDebugValue: Se,
    useDeferredValue: Se,
    useTransition: Se,
    useMutableSource: Se,
    useSyncExternalStore: Se,
    useId: Se,
    unstable_isNewReconciler: !1
}
  , mh = {
    readContext: Xe,
    useCallback: function(e, t) {
        return st().memoizedState = [e, t === void 0 ? null : t],
        e
    },
    useContext: Xe,
    useEffect: na,
    useImperativeHandle: function(e, t, n) {
        return n = n != null ? n.concat([e]) : null,
        Cl(4194308, 4, ed.bind(null, t, e), n)
    },
    useLayoutEffect: function(e, t) {
        return Cl(4194308, 4, e, t)
    },
    useInsertionEffect: function(e, t) {
        return Cl(4, 2, e, t)
    },
    useMemo: function(e, t) {
        var n = st();
        return t = t === void 0 ? null : t,
        e = e(),
        n.memoizedState = [e, t],
        e
    },
    useReducer: function(e, t, n) {
        var r = st();
        return t = n !== void 0 ? n(t) : t,
        r.memoizedState = r.baseState = t,
        e = {
            pending: null,
            interleaved: null,
            lanes: 0,
            dispatch: null,
            lastRenderedReducer: e,
            lastRenderedState: t
        },
        r.queue = e,
        e = e.dispatch = ph.bind(null, ie, e),
        [r.memoizedState, e]
    },
    useRef: function(e) {
        var t = st();
        return e = {
            current: e
        },
        t.memoizedState = e
    },
    useState: ta,
    useDebugValue: Is,
    useDeferredValue: function(e) {
        return st().memoizedState = e
    },
    useTransition: function() {
        var e = ta(!1)
          , t = e[0];
        return e = fh.bind(null, e[1]),
        st().memoizedState = e,
        [t, e]
    },
    useMutableSource: function() {},
    useSyncExternalStore: function(e, t, n) {
        var r = ie
          , l = st();
        if (le) {
            if (n === void 0)
                throw Error(w(407));
            n = n()
        } else {
            if (n = t(),
            me === null)
                throw Error(w(349));
            on & 30 || Kc(r, t, n)
        }
        l.memoizedState = n;
        var o = {
            value: n,
            getSnapshot: t
        };
        return l.queue = o,
        na(Xc.bind(null, r, o, e), [e]),
        r.flags |= 2048,
        Ir(9, Yc.bind(null, r, o, n, t), void 0, null),
        n
    },
    useId: function() {
        var e = st()
          , t = me.identifierPrefix;
        if (le) {
            var n = yt
              , r = mt;
            n = (r & ~(1 << 32 - et(r) - 1)).toString(32) + n,
            t = ":" + t + "R" + n,
            n = Nr++,
            0 < n && (t += "H" + n.toString(32)),
            t += ":"
        } else
            n = dh++,
            t = ":" + t + "r" + n.toString(32) + ":";
        return e.memoizedState = t
    },
    unstable_isNewReconciler: !1
}
  , yh = {
    readContext: Xe,
    useCallback: nd,
    useContext: Xe,
    useEffect: Fs,
    useImperativeHandle: td,
    useInsertionEffect: qc,
    useLayoutEffect: bc,
    useMemo: rd,
    useReducer: Xo,
    useRef: Zc,
    useState: function() {
        return Xo(Fr)
    },
    useDebugValue: Is,
    useDeferredValue: function(e) {
        var t = Ge();
        return ld(t, fe.memoizedState, e)
    },
    useTransition: function() {
        var e = Xo(Fr)[0]
          , t = Ge().memoizedState;
        return [e, t]
    },
    useMutableSource: Vc,
    useSyncExternalStore: Qc,
    useId: od,
    unstable_isNewReconciler: !1
}
  , gh = {
    readContext: Xe,
    useCallback: nd,
    useContext: Xe,
    useEffect: Fs,
    useImperativeHandle: td,
    useInsertionEffect: qc,
    useLayoutEffect: bc,
    useMemo: rd,
    useReducer: Go,
    useRef: Zc,
    useState: function() {
        return Go(Fr)
    },
    useDebugValue: Is,
    useDeferredValue: function(e) {
        var t = Ge();
        return fe === null ? t.memoizedState = e : ld(t, fe.memoizedState, e)
    },
    useTransition: function() {
        var e = Go(Fr)[0]
          , t = Ge().memoizedState;
        return [e, t]
    },
    useMutableSource: Vc,
    useSyncExternalStore: Qc,
    useId: od,
    unstable_isNewReconciler: !1
};
function Ze(e, t) {
    if (e && e.defaultProps) {
        t = se({}, t),
        e = e.defaultProps;
        for (var n in e)
            t[n] === void 0 && (t[n] = e[n]);
        return t
    }
    return t
}
function Oi(e, t, n, r) {
    t = e.memoizedState,
    n = n(r, t),
    n = n == null ? t : se({}, t, n),
    e.memoizedState = n,
    e.lanes === 0 && (e.updateQueue.baseState = n)
}
var io = {
    isMounted: function(e) {
        return (e = e._reactInternals) ? cn(e) === e : !1
    },
    enqueueSetState: function(e, t, n) {
        e = e._reactInternals;
        var r = _e()
          , l = Wt(e)
          , o = gt(r, l);
        o.payload = t,
        n != null && (o.callback = n),
        t = Mt(e, o, l),
        t !== null && (tt(t, e, l, r),
        kl(t, e, l))
    },
    enqueueReplaceState: function(e, t, n) {
        e = e._reactInternals;
        var r = _e()
          , l = Wt(e)
          , o = gt(r, l);
        o.tag = 1,
        o.payload = t,
        n != null && (o.callback = n),
        t = Mt(e, o, l),
        t !== null && (tt(t, e, l, r),
        kl(t, e, l))
    },
    enqueueForceUpdate: function(e, t) {
        e = e._reactInternals;
        var n = _e()
          , r = Wt(e)
          , l = gt(n, r);
        l.tag = 2,
        t != null && (l.callback = t),
        t = Mt(e, l, r),
        t !== null && (tt(t, e, r, n),
        kl(t, e, r))
    }
};
function ra(e, t, n, r, l, o, i) {
    return e = e.stateNode,
    typeof e.shouldComponentUpdate == "function" ? e.shouldComponentUpdate(r, o, i) : t.prototype && t.prototype.isPureReactComponent ? !Er(n, r) || !Er(l, o) : !0
}
function ad(e, t, n) {
    var r = !1
      , l = Ut
      , o = t.contextType;
    return typeof o == "object" && o !== null ? o = Xe(o) : (l = De(t) ? rn : Ce.current,
    r = t.contextTypes,
    o = (r = r != null) ? Wn(e, l) : Ut),
    t = new t(n,o),
    e.memoizedState = t.state !== null && t.state !== void 0 ? t.state : null,
    t.updater = io,
    e.stateNode = t,
    t._reactInternals = e,
    r && (e = e.stateNode,
    e.__reactInternalMemoizedUnmaskedChildContext = l,
    e.__reactInternalMemoizedMaskedChildContext = o),
    t
}
function la(e, t, n, r) {
    e = t.state,
    typeof t.componentWillReceiveProps == "function" && t.componentWillReceiveProps(n, r),
    typeof t.UNSAFE_componentWillReceiveProps == "function" && t.UNSAFE_componentWillReceiveProps(n, r),
    t.state !== e && io.enqueueReplaceState(t, t.state, null)
}
function Mi(e, t, n, r) {
    var l = e.stateNode;
    l.props = n,
    l.state = e.memoizedState,
    l.refs = {},
    Es(e);
    var o = t.contextType;
    typeof o == "object" && o !== null ? l.context = Xe(o) : (o = De(t) ? rn : Ce.current,
    l.context = Wn(e, o)),
    l.state = e.memoizedState,
    o = t.getDerivedStateFromProps,
    typeof o == "function" && (Oi(e, t, o, n),
    l.state = e.memoizedState),
    typeof t.getDerivedStateFromProps == "function" || typeof l.getSnapshotBeforeUpdate == "function" || typeof l.UNSAFE_componentWillMount != "function" && typeof l.componentWillMount != "function" || (t = l.state,
    typeof l.componentWillMount == "function" && l.componentWillMount(),
    typeof l.UNSAFE_componentWillMount == "function" && l.UNSAFE_componentWillMount(),
    t !== l.state && io.enqueueReplaceState(l, l.state, null),
    Hl(e, n, l, r),
    l.state = e.memoizedState),
    typeof l.componentDidMount == "function" && (e.flags |= 4194308)
}
function Hn(e, t) {
    try {
        var n = ""
          , r = t;
        do
            n += Qf(r),
            r = r.return;
        while (r);
        var l = n
    } catch (o) {
        l = `
Error generating stack: ` + o.message + `
` + o.stack
    }
    return {
        value: e,
        source: t,
        stack: l,
        digest: null
    }
}
function Jo(e, t, n) {
    return {
        value: e,
        source: null,
        stack: n ?? null,
        digest: t ?? null
    }
}
function Ai(e, t) {
    try {
        console.error(t.value)
    } catch (n) {
        setTimeout(function() {
            throw n
        })
    }
}
var vh = typeof WeakMap == "function" ? WeakMap : Map;
function cd(e, t, n) {
    n = gt(-1, n),
    n.tag = 3,
    n.payload = {
        element: null
    };
    var r = t.value;
    return n.callback = function() {
        Xl || (Xl = !0,
        Xi = r),
        Ai(e, t)
    }
    ,
    n
}
function dd(e, t, n) {
    n = gt(-1, n),
    n.tag = 3;
    var r = e.type.getDerivedStateFromError;
    if (typeof r == "function") {
        var l = t.value;
        n.payload = function() {
            return r(l)
        }
        ,
        n.callback = function() {
            Ai(e, t)
        }
    }
    var o = e.stateNode;
    return o !== null && typeof o.componentDidCatch == "function" && (n.callback = function() {
        Ai(e, t),
        typeof r != "function" && (At === null ? At = new Set([this]) : At.add(this));
        var i = t.stack;
        this.componentDidCatch(t.value, {
            componentStack: i !== null ? i : ""
        })
    }
    ),
    n
}
function oa(e, t, n) {
    var r = e.pingCache;
    if (r === null) {
        r = e.pingCache = new vh;
        var l = new Set;
        r.set(t, l)
    } else
        l = r.get(t),
        l === void 0 && (l = new Set,
        r.set(t, l));
    l.has(n) || (l.add(n),
    e = Fh.bind(null, e, t, n),
    t.then(e, e))
}
function ia(e) {
    do {
        var t;
        if ((t = e.tag === 13) && (t = e.memoizedState,
        t = t !== null ? t.dehydrated !== null : !0),
        t)
            return e;
        e = e.return
    } while (e !== null);
    return null
}
function sa(e, t, n, r, l) {
    return e.mode & 1 ? (e.flags |= 65536,
    e.lanes = l,
    e) : (e === t ? e.flags |= 65536 : (e.flags |= 128,
    n.flags |= 131072,
    n.flags &= -52805,
    n.tag === 1 && (n.alternate === null ? n.tag = 17 : (t = gt(-1, 1),
    t.tag = 2,
    Mt(n, t, 1))),
    n.lanes |= 1),
    e)
}
var xh = wt.ReactCurrentOwner
  , Ie = !1;
function ze(e, t, n, r) {
    t.child = e === null ? Bc(t, null, n, r) : $n(t, e.child, n, r)
}
function ua(e, t, n, r, l) {
    n = n.render;
    var o = t.ref;
    return On(t, l),
    r = Ps(e, t, n, r, o, l),
    n = Ns(),
    e !== null && !Ie ? (t.updateQueue = e.updateQueue,
    t.flags &= -2053,
    e.lanes &= ~l,
    kt(e, t, l)) : (le && n && vs(t),
    t.flags |= 1,
    ze(e, t, r, l),
    t.child)
}
function aa(e, t, n, r, l) {
    if (e === null) {
        var o = n.type;
        return typeof o == "function" && !$s(o) && o.defaultProps === void 0 && n.compare === null && n.defaultProps === void 0 ? (t.tag = 15,
        t.type = o,
        fd(e, t, o, r, l)) : (e = _l(n.type, null, r, t, t.mode, l),
        e.ref = t.ref,
        e.return = t,
        t.child = e)
    }
    if (o = e.child,
    !(e.lanes & l)) {
        var i = o.memoizedProps;
        if (n = n.compare,
        n = n !== null ? n : Er,
        n(i, r) && e.ref === t.ref)
            return kt(e, t, l)
    }
    return t.flags |= 1,
    e = Bt(o, r),
    e.ref = t.ref,
    e.return = t,
    t.child = e
}
function fd(e, t, n, r, l) {
    if (e !== null) {
        var o = e.memoizedProps;
        if (Er(o, r) && e.ref === t.ref)
            if (Ie = !1,
            t.pendingProps = r = o,
            (e.lanes & l) !== 0)
                e.flags & 131072 && (Ie = !0);
            else
                return t.lanes = e.lanes,
                kt(e, t, l)
    }
    return Wi(e, t, n, r, l)
}
function pd(e, t, n) {
    var r = t.pendingProps
      , l = r.children
      , o = e !== null ? e.memoizedState : null;
    if (r.mode === "hidden")
        if (!(t.mode & 1))
            t.memoizedState = {
                baseLanes: 0,
                cachePool: null,
                transitions: null
            },
            q(Nn, Me),
            Me |= n;
        else {
            if (!(n & 1073741824))
                return e = o !== null ? o.baseLanes | n : n,
                t.lanes = t.childLanes = 1073741824,
                t.memoizedState = {
                    baseLanes: e,
                    cachePool: null,
                    transitions: null
                },
                t.updateQueue = null,
                q(Nn, Me),
                Me |= e,
                null;
            t.memoizedState = {
                baseLanes: 0,
                cachePool: null,
                transitions: null
            },
            r = o !== null ? o.baseLanes : n,
            q(Nn, Me),
            Me |= r
        }
    else
        o !== null ? (r = o.baseLanes | n,
        t.memoizedState = null) : r = n,
        q(Nn, Me),
        Me |= r;
    return ze(e, t, l, n),
    t.child
}
function hd(e, t) {
    var n = t.ref;
    (e === null && n !== null || e !== null && e.ref !== n) && (t.flags |= 512,
    t.flags |= 2097152)
}
function Wi(e, t, n, r, l) {
    var o = De(n) ? rn : Ce.current;
    return o = Wn(t, o),
    On(t, l),
    n = Ps(e, t, n, r, o, l),
    r = Ns(),
    e !== null && !Ie ? (t.updateQueue = e.updateQueue,
    t.flags &= -2053,
    e.lanes &= ~l,
    kt(e, t, l)) : (le && r && vs(t),
    t.flags |= 1,
    ze(e, t, n, l),
    t.child)
}
function ca(e, t, n, r, l) {
    if (De(n)) {
        var o = !0;
        Al(t)
    } else
        o = !1;
    if (On(t, l),
    t.stateNode === null)
        jl(e, t),
        ad(t, n, r),
        Mi(t, n, r, l),
        r = !0;
    else if (e === null) {
        var i = t.stateNode
          , u = t.memoizedProps;
        i.props = u;
        var c = i.context
          , f = n.contextType;
        typeof f == "object" && f !== null ? f = Xe(f) : (f = De(n) ? rn : Ce.current,
        f = Wn(t, f));
        var v = n.getDerivedStateFromProps
          , g = typeof v == "function" || typeof i.getSnapshotBeforeUpdate == "function";
        g || typeof i.UNSAFE_componentWillReceiveProps != "function" && typeof i.componentWillReceiveProps != "function" || (u !== r || c !== f) && la(t, i, r, f),
        Lt = !1;
        var y = t.memoizedState;
        i.state = y,
        Hl(t, r, i, l),
        c = t.memoizedState,
        u !== r || y !== c || Re.current || Lt ? (typeof v == "function" && (Oi(t, n, v, r),
        c = t.memoizedState),
        (u = Lt || ra(t, n, u, r, y, c, f)) ? (g || typeof i.UNSAFE_componentWillMount != "function" && typeof i.componentWillMount != "function" || (typeof i.componentWillMount == "function" && i.componentWillMount(),
        typeof i.UNSAFE_componentWillMount == "function" && i.UNSAFE_componentWillMount()),
        typeof i.componentDidMount == "function" && (t.flags |= 4194308)) : (typeof i.componentDidMount == "function" && (t.flags |= 4194308),
        t.memoizedProps = r,
        t.memoizedState = c),
        i.props = r,
        i.state = c,
        i.context = f,
        r = u) : (typeof i.componentDidMount == "function" && (t.flags |= 4194308),
        r = !1)
    } else {
        i = t.stateNode,
        Uc(e, t),
        u = t.memoizedProps,
        f = t.type === t.elementType ? u : Ze(t.type, u),
        i.props = f,
        g = t.pendingProps,
        y = i.context,
        c = n.contextType,
        typeof c == "object" && c !== null ? c = Xe(c) : (c = De(n) ? rn : Ce.current,
        c = Wn(t, c));
        var C = n.getDerivedStateFromProps;
        (v = typeof C == "function" || typeof i.getSnapshotBeforeUpdate == "function") || typeof i.UNSAFE_componentWillReceiveProps != "function" && typeof i.componentWillReceiveProps != "function" || (u !== g || y !== c) && la(t, i, r, c),
        Lt = !1,
        y = t.memoizedState,
        i.state = y,
        Hl(t, r, i, l);
        var j = t.memoizedState;
        u !== g || y !== j || Re.current || Lt ? (typeof C == "function" && (Oi(t, n, C, r),
        j = t.memoizedState),
        (f = Lt || ra(t, n, f, r, y, j, c) || !1) ? (v || typeof i.UNSAFE_componentWillUpdate != "function" && typeof i.componentWillUpdate != "function" || (typeof i.componentWillUpdate == "function" && i.componentWillUpdate(r, j, c),
        typeof i.UNSAFE_componentWillUpdate == "function" && i.UNSAFE_componentWillUpdate(r, j, c)),
        typeof i.componentDidUpdate == "function" && (t.flags |= 4),
        typeof i.getSnapshotBeforeUpdate == "function" && (t.flags |= 1024)) : (typeof i.componentDidUpdate != "function" || u === e.memoizedProps && y === e.memoizedState || (t.flags |= 4),
        typeof i.getSnapshotBeforeUpdate != "function" || u === e.memoizedProps && y === e.memoizedState || (t.flags |= 1024),
        t.memoizedProps = r,
        t.memoizedState = j),
        i.props = r,
        i.state = j,
        i.context = c,
        r = f) : (typeof i.componentDidUpdate != "function" || u === e.memoizedProps && y === e.memoizedState || (t.flags |= 4),
        typeof i.getSnapshotBeforeUpdate != "function" || u === e.memoizedProps && y === e.memoizedState || (t.flags |= 1024),
        r = !1)
    }
    return Bi(e, t, n, r, o, l)
}
function Bi(e, t, n, r, l, o) {
    hd(e, t);
    var i = (t.flags & 128) !== 0;
    if (!r && !i)
        return l && Gu(t, n, !1),
        kt(e, t, o);
    r = t.stateNode,
    xh.current = t;
    var u = i && typeof n.getDerivedStateFromError != "function" ? null : r.render();
    return t.flags |= 1,
    e !== null && i ? (t.child = $n(t, e.child, null, o),
    t.child = $n(t, null, u, o)) : ze(e, t, u, o),
    t.memoizedState = r.state,
    l && Gu(t, n, !0),
    t.child
}
function md(e) {
    var t = e.stateNode;
    t.pendingContext ? Xu(e, t.pendingContext, t.pendingContext !== t.context) : t.context && Xu(e, t.context, !1),
    zs(e, t.containerInfo)
}
function da(e, t, n, r, l) {
    return Bn(),
    Ss(l),
    t.flags |= 256,
    ze(e, t, n, r),
    t.child
}
var $i = {
    dehydrated: null,
    treeContext: null,
    retryLane: 0
};
function Ui(e) {
    return {
        baseLanes: e,
        cachePool: null,
        transitions: null
    }
}
function yd(e, t, n) {
    var r = t.pendingProps, l = oe.current, o = !1, i = (t.flags & 128) !== 0, u;
    if ((u = i) || (u = e !== null && e.memoizedState === null ? !1 : (l & 2) !== 0),
    u ? (o = !0,
    t.flags &= -129) : (e === null || e.memoizedState !== null) && (l |= 1),
    q(oe, l & 1),
    e === null)
        return Ri(t),
        e = t.memoizedState,
        e !== null && (e = e.dehydrated,
        e !== null) ? (t.mode & 1 ? e.data === "$!" ? t.lanes = 8 : t.lanes = 1073741824 : t.lanes = 1,
        null) : (i = r.children,
        e = r.fallback,
        o ? (r = t.mode,
        o = t.child,
        i = {
            mode: "hidden",
            children: i
        },
        !(r & 1) && o !== null ? (o.childLanes = 0,
        o.pendingProps = i) : o = ao(i, r, 0, null),
        e = tn(e, r, n, null),
        o.return = t,
        e.return = t,
        o.sibling = e,
        t.child = o,
        t.child.memoizedState = Ui(n),
        t.memoizedState = $i,
        e) : Rs(t, i));
    if (l = e.memoizedState,
    l !== null && (u = l.dehydrated,
    u !== null))
        return Sh(e, t, i, r, u, l, n);
    if (o) {
        o = r.fallback,
        i = t.mode,
        l = e.child,
        u = l.sibling;
        var c = {
            mode: "hidden",
            children: r.children
        };
        return !(i & 1) && t.child !== l ? (r = t.child,
        r.childLanes = 0,
        r.pendingProps = c,
        t.deletions = null) : (r = Bt(l, c),
        r.subtreeFlags = l.subtreeFlags & 14680064),
        u !== null ? o = Bt(u, o) : (o = tn(o, i, n, null),
        o.flags |= 2),
        o.return = t,
        r.return = t,
        r.sibling = o,
        t.child = r,
        r = o,
        o = t.child,
        i = e.child.memoizedState,
        i = i === null ? Ui(n) : {
            baseLanes: i.baseLanes | n,
            cachePool: null,
            transitions: i.transitions
        },
        o.memoizedState = i,
        o.childLanes = e.childLanes & ~n,
        t.memoizedState = $i,
        r
    }
    return o = e.child,
    e = o.sibling,
    r = Bt(o, {
        mode: "visible",
        children: r.children
    }),
    !(t.mode & 1) && (r.lanes = n),
    r.return = t,
    r.sibling = null,
    e !== null && (n = t.deletions,
    n === null ? (t.deletions = [e],
    t.flags |= 16) : n.push(e)),
    t.child = r,
    t.memoizedState = null,
    r
}
function Rs(e, t) {
    return t = ao({
        mode: "visible",
        children: t
    }, e.mode, 0, null),
    t.return = e,
    e.child = t
}
function cl(e, t, n, r) {
    return r !== null && Ss(r),
    $n(t, e.child, null, n),
    e = Rs(t, t.pendingProps.children),
    e.flags |= 2,
    t.memoizedState = null,
    e
}
function Sh(e, t, n, r, l, o, i) {
    if (n)
        return t.flags & 256 ? (t.flags &= -257,
        r = Jo(Error(w(422))),
        cl(e, t, i, r)) : t.memoizedState !== null ? (t.child = e.child,
        t.flags |= 128,
        null) : (o = r.fallback,
        l = t.mode,
        r = ao({
            mode: "visible",
            children: r.children
        }, l, 0, null),
        o = tn(o, l, i, null),
        o.flags |= 2,
        r.return = t,
        o.return = t,
        r.sibling = o,
        t.child = r,
        t.mode & 1 && $n(t, e.child, null, i),
        t.child.memoizedState = Ui(i),
        t.memoizedState = $i,
        o);
    if (!(t.mode & 1))
        return cl(e, t, i, null);
    if (l.data === "$!") {
        if (r = l.nextSibling && l.nextSibling.dataset,
        r)
            var u = r.dgst;
        return r = u,
        o = Error(w(419)),
        r = Jo(o, r, void 0),
        cl(e, t, i, r)
    }
    if (u = (i & e.childLanes) !== 0,
    Ie || u) {
        if (r = me,
        r !== null) {
            switch (i & -i) {
            case 4:
                l = 2;
                break;
            case 16:
                l = 8;
                break;
            case 64:
            case 128:
            case 256:
            case 512:
            case 1024:
            case 2048:
            case 4096:
            case 8192:
            case 16384:
            case 32768:
            case 65536:
            case 131072:
            case 262144:
            case 524288:
            case 1048576:
            case 2097152:
            case 4194304:
            case 8388608:
            case 16777216:
            case 33554432:
            case 67108864:
                l = 32;
                break;
            case 536870912:
                l = 268435456;
                break;
            default:
                l = 0
            }
            l = l & (r.suspendedLanes | i) ? 0 : l,
            l !== 0 && l !== o.retryLane && (o.retryLane = l,
            St(e, l),
            tt(r, e, l, -1))
        }
        return Bs(),
        r = Jo(Error(w(421))),
        cl(e, t, i, r)
    }
    return l.data === "$?" ? (t.flags |= 128,
    t.child = e.child,
    t = Ih.bind(null, e),
    l._reactRetry = t,
    null) : (e = o.treeContext,
    Ae = Ot(l.nextSibling),
    We = t,
    le = !0,
    be = null,
    e !== null && (Ve[Qe++] = mt,
    Ve[Qe++] = yt,
    Ve[Qe++] = ln,
    mt = e.id,
    yt = e.overflow,
    ln = t),
    t = Rs(t, r.children),
    t.flags |= 4096,
    t)
}
function fa(e, t, n) {
    e.lanes |= t;
    var r = e.alternate;
    r !== null && (r.lanes |= t),
    Di(e.return, t, n)
}
function Zo(e, t, n, r, l) {
    var o = e.memoizedState;
    o === null ? e.memoizedState = {
        isBackwards: t,
        rendering: null,
        renderingStartTime: 0,
        last: r,
        tail: n,
        tailMode: l
    } : (o.isBackwards = t,
    o.rendering = null,
    o.renderingStartTime = 0,
    o.last = r,
    o.tail = n,
    o.tailMode = l)
}
function gd(e, t, n) {
    var r = t.pendingProps
      , l = r.revealOrder
      , o = r.tail;
    if (ze(e, t, r.children, n),
    r = oe.current,
    r & 2)
        r = r & 1 | 2,
        t.flags |= 128;
    else {
        if (e !== null && e.flags & 128)
            e: for (e = t.child; e !== null; ) {
                if (e.tag === 13)
                    e.memoizedState !== null && fa(e, n, t);
                else if (e.tag === 19)
                    fa(e, n, t);
                else if (e.child !== null) {
                    e.child.return = e,
                    e = e.child;
                    continue
                }
                if (e === t)
                    break e;
                for (; e.sibling === null; ) {
                    if (e.return === null || e.return === t)
                        break e;
                    e = e.return
                }
                e.sibling.return = e.return,
                e = e.sibling
            }
        r &= 1
    }
    if (q(oe, r),
    !(t.mode & 1))
        t.memoizedState = null;
    else
        switch (l) {
        case "forwards":
            for (n = t.child,
            l = null; n !== null; )
                e = n.alternate,
                e !== null && Vl(e) === null && (l = n),
                n = n.sibling;
            n = l,
            n === null ? (l = t.child,
            t.child = null) : (l = n.sibling,
            n.sibling = null),
            Zo(t, !1, l, n, o);
            break;
        case "backwards":
            for (n = null,
            l = t.child,
            t.child = null; l !== null; ) {
                if (e = l.alternate,
                e !== null && Vl(e) === null) {
                    t.child = l;
                    break
                }
                e = l.sibling,
                l.sibling = n,
                n = l,
                l = e
            }
            Zo(t, !0, n, null, o);
            break;
        case "together":
            Zo(t, !1, null, null, void 0);
            break;
        default:
            t.memoizedState = null
        }
    return t.child
}
function jl(e, t) {
    !(t.mode & 1) && e !== null && (e.alternate = null,
    t.alternate = null,
    t.flags |= 2)
}
function kt(e, t, n) {
    if (e !== null && (t.dependencies = e.dependencies),
    sn |= t.lanes,
    !(n & t.childLanes))
        return null;
    if (e !== null && t.child !== e.child)
        throw Error(w(153));
    if (t.child !== null) {
        for (e = t.child,
        n = Bt(e, e.pendingProps),
        t.child = n,
        n.return = t; e.sibling !== null; )
            e = e.sibling,
            n = n.sibling = Bt(e, e.pendingProps),
            n.return = t;
        n.sibling = null
    }
    return t.child
}
function kh(e, t, n) {
    switch (t.tag) {
    case 3:
        md(t),
        Bn();
        break;
    case 5:
        Hc(t);
        break;
    case 1:
        De(t.type) && Al(t);
        break;
    case 4:
        zs(t, t.stateNode.containerInfo);
        break;
    case 10:
        var r = t.type._context
          , l = t.memoizedProps.value;
        q($l, r._currentValue),
        r._currentValue = l;
        break;
    case 13:
        if (r = t.memoizedState,
        r !== null)
            return r.dehydrated !== null ? (q(oe, oe.current & 1),
            t.flags |= 128,
            null) : n & t.child.childLanes ? yd(e, t, n) : (q(oe, oe.current & 1),
            e = kt(e, t, n),
            e !== null ? e.sibling : null);
        q(oe, oe.current & 1);
        break;
    case 19:
        if (r = (n & t.childLanes) !== 0,
        e.flags & 128) {
            if (r)
                return gd(e, t, n);
            t.flags |= 128
        }
        if (l = t.memoizedState,
        l !== null && (l.rendering = null,
        l.tail = null,
        l.lastEffect = null),
        q(oe, oe.current),
        r)
            break;
        return null;
    case 22:
    case 23:
        return t.lanes = 0,
        pd(e, t, n)
    }
    return kt(e, t, n)
}
var vd, Hi, xd, Sd;
vd = function(e, t) {
    for (var n = t.child; n !== null; ) {
        if (n.tag === 5 || n.tag === 6)
            e.appendChild(n.stateNode);
        else if (n.tag !== 4 && n.child !== null) {
            n.child.return = n,
            n = n.child;
            continue
        }
        if (n === t)
            break;
        for (; n.sibling === null; ) {
            if (n.return === null || n.return === t)
                return;
            n = n.return
        }
        n.sibling.return = n.return,
        n = n.sibling
    }
}
;
Hi = function() {}
;
xd = function(e, t, n, r) {
    var l = e.memoizedProps;
    if (l !== r) {
        e = t.stateNode,
        bt(ct.current);
        var o = null;
        switch (n) {
        case "input":
            l = di(e, l),
            r = di(e, r),
            o = [];
            break;
        case "select":
            l = se({}, l, {
                value: void 0
            }),
            r = se({}, r, {
                value: void 0
            }),
            o = [];
            break;
        case "textarea":
            l = hi(e, l),
            r = hi(e, r),
            o = [];
            break;
        default:
            typeof l.onClick != "function" && typeof r.onClick == "function" && (e.onclick = Ol)
        }
        yi(n, r);
        var i;
        n = null;
        for (f in l)
            if (!r.hasOwnProperty(f) && l.hasOwnProperty(f) && l[f] != null)
                if (f === "style") {
                    var u = l[f];
                    for (i in u)
                        u.hasOwnProperty(i) && (n || (n = {}),
                        n[i] = "")
                } else
                    f !== "dangerouslySetInnerHTML" && f !== "children" && f !== "suppressContentEditableWarning" && f !== "suppressHydrationWarning" && f !== "autoFocus" && (vr.hasOwnProperty(f) ? o || (o = []) : (o = o || []).push(f, null));
        for (f in r) {
            var c = r[f];
            if (u = l != null ? l[f] : void 0,
            r.hasOwnProperty(f) && c !== u && (c != null || u != null))
                if (f === "style")
                    if (u) {
                        for (i in u)
                            !u.hasOwnProperty(i) || c && c.hasOwnProperty(i) || (n || (n = {}),
                            n[i] = "");
                        for (i in c)
                            c.hasOwnProperty(i) && u[i] !== c[i] && (n || (n = {}),
                            n[i] = c[i])
                    } else
                        n || (o || (o = []),
                        o.push(f, n)),
                        n = c;
                else
                    f === "dangerouslySetInnerHTML" ? (c = c ? c.__html : void 0,
                    u = u ? u.__html : void 0,
                    c != null && u !== c && (o = o || []).push(f, c)) : f === "children" ? typeof c != "string" && typeof c != "number" || (o = o || []).push(f, "" + c) : f !== "suppressContentEditableWarning" && f !== "suppressHydrationWarning" && (vr.hasOwnProperty(f) ? (c != null && f === "onScroll" && b("scroll", e),
                    o || u === c || (o = [])) : (o = o || []).push(f, c))
        }
        n && (o = o || []).push("style", n);
        var f = o;
        (t.updateQueue = f) && (t.flags |= 4)
    }
}
;
Sd = function(e, t, n, r) {
    n !== r && (t.flags |= 4)
}
;
function nr(e, t) {
    if (!le)
        switch (e.tailMode) {
        case "hidden":
            t = e.tail;
            for (var n = null; t !== null; )
                t.alternate !== null && (n = t),
                t = t.sibling;
            n === null ? e.tail = null : n.sibling = null;
            break;
        case "collapsed":
            n = e.tail;
            for (var r = null; n !== null; )
                n.alternate !== null && (r = n),
                n = n.sibling;
            r === null ? t || e.tail === null ? e.tail = null : e.tail.sibling = null : r.sibling = null
        }
}
function ke(e) {
    var t = e.alternate !== null && e.alternate.child === e.child
      , n = 0
      , r = 0;
    if (t)
        for (var l = e.child; l !== null; )
            n |= l.lanes | l.childLanes,
            r |= l.subtreeFlags & 14680064,
            r |= l.flags & 14680064,
            l.return = e,
            l = l.sibling;
    else
        for (l = e.child; l !== null; )
            n |= l.lanes | l.childLanes,
            r |= l.subtreeFlags,
            r |= l.flags,
            l.return = e,
            l = l.sibling;
    return e.subtreeFlags |= r,
    e.childLanes = n,
    t
}
function wh(e, t, n) {
    var r = t.pendingProps;
    switch (xs(t),
    t.tag) {
    case 2:
    case 16:
    case 15:
    case 0:
    case 11:
    case 7:
    case 8:
    case 12:
    case 9:
    case 14:
        return ke(t),
        null;
    case 1:
        return De(t.type) && Ml(),
        ke(t),
        null;
    case 3:
        return r = t.stateNode,
        Un(),
        ee(Re),
        ee(Ce),
        Ls(),
        r.pendingContext && (r.context = r.pendingContext,
        r.pendingContext = null),
        (e === null || e.child === null) && (ul(t) ? t.flags |= 4 : e === null || e.memoizedState.isDehydrated && !(t.flags & 256) || (t.flags |= 1024,
        be !== null && (Zi(be),
        be = null))),
        Hi(e, t),
        ke(t),
        null;
    case 5:
        _s(t);
        var l = bt(Pr.current);
        if (n = t.type,
        e !== null && t.stateNode != null)
            xd(e, t, n, r, l),
            e.ref !== t.ref && (t.flags |= 512,
            t.flags |= 2097152);
        else {
            if (!r) {
                if (t.stateNode === null)
                    throw Error(w(166));
                return ke(t),
                null
            }
            if (e = bt(ct.current),
            ul(t)) {
                r = t.stateNode,
                n = t.type;
                var o = t.memoizedProps;
                switch (r[ut] = t,
                r[Lr] = o,
                e = (t.mode & 1) !== 0,
                n) {
                case "dialog":
                    b("cancel", r),
                    b("close", r);
                    break;
                case "iframe":
                case "object":
                case "embed":
                    b("load", r);
                    break;
                case "video":
                case "audio":
                    for (l = 0; l < ur.length; l++)
                        b(ur[l], r);
                    break;
                case "source":
                    b("error", r);
                    break;
                case "img":
                case "image":
                case "link":
                    b("error", r),
                    b("load", r);
                    break;
                case "details":
                    b("toggle", r);
                    break;
                case "input":
                    ku(r, o),
                    b("invalid", r);
                    break;
                case "select":
                    r._wrapperState = {
                        wasMultiple: !!o.multiple
                    },
                    b("invalid", r);
                    break;
                case "textarea":
                    Cu(r, o),
                    b("invalid", r)
                }
                yi(n, o),
                l = null;
                for (var i in o)
                    if (o.hasOwnProperty(i)) {
                        var u = o[i];
                        i === "children" ? typeof u == "string" ? r.textContent !== u && (o.suppressHydrationWarning !== !0 && sl(r.textContent, u, e),
                        l = ["children", u]) : typeof u == "number" && r.textContent !== "" + u && (o.suppressHydrationWarning !== !0 && sl(r.textContent, u, e),
                        l = ["children", "" + u]) : vr.hasOwnProperty(i) && u != null && i === "onScroll" && b("scroll", r)
                    }
                switch (n) {
                case "input":
                    br(r),
                    wu(r, o, !0);
                    break;
                case "textarea":
                    br(r),
                    ju(r);
                    break;
                case "select":
                case "option":
                    break;
                default:
                    typeof o.onClick == "function" && (r.onclick = Ol)
                }
                r = l,
                t.updateQueue = r,
                r !== null && (t.flags |= 4)
            } else {
                i = l.nodeType === 9 ? l : l.ownerDocument,
                e === "http://www.w3.org/1999/xhtml" && (e = Xa(n)),
                e === "http://www.w3.org/1999/xhtml" ? n === "script" ? (e = i.createElement("div"),
                e.innerHTML = "<script><\/script>",
                e = e.removeChild(e.firstChild)) : typeof r.is == "string" ? e = i.createElement(n, {
                    is: r.is
                }) : (e = i.createElement(n),
                n === "select" && (i = e,
                r.multiple ? i.multiple = !0 : r.size && (i.size = r.size))) : e = i.createElementNS(e, n),
                e[ut] = t,
                e[Lr] = r,
                vd(e, t, !1, !1),
                t.stateNode = e;
                e: {
                    switch (i = gi(n, r),
                    n) {
                    case "dialog":
                        b("cancel", e),
                        b("close", e),
                        l = r;
                        break;
                    case "iframe":
                    case "object":
                    case "embed":
                        b("load", e),
                        l = r;
                        break;
                    case "video":
                    case "audio":
                        for (l = 0; l < ur.length; l++)
                            b(ur[l], e);
                        l = r;
                        break;
                    case "source":
                        b("error", e),
                        l = r;
                        break;
                    case "img":
                    case "image":
                    case "link":
                        b("error", e),
                        b("load", e),
                        l = r;
                        break;
                    case "details":
                        b("toggle", e),
                        l = r;
                        break;
                    case "input":
                        ku(e, r),
                        l = di(e, r),
                        b("invalid", e);
                        break;
                    case "option":
                        l = r;
                        break;
                    case "select":
                        e._wrapperState = {
                            wasMultiple: !!r.multiple
                        },
                        l = se({}, r, {
                            value: void 0
                        }),
                        b("invalid", e);
                        break;
                    case "textarea":
                        Cu(e, r),
                        l = hi(e, r),
                        b("invalid", e);
                        break;
                    default:
                        l = r
                    }
                    yi(n, l),
                    u = l;
                    for (o in u)
                        if (u.hasOwnProperty(o)) {
                            var c = u[o];
                            o === "style" ? Za(e, c) : o === "dangerouslySetInnerHTML" ? (c = c ? c.__html : void 0,
                            c != null && Ga(e, c)) : o === "children" ? typeof c == "string" ? (n !== "textarea" || c !== "") && xr(e, c) : typeof c == "number" && xr(e, "" + c) : o !== "suppressContentEditableWarning" && o !== "suppressHydrationWarning" && o !== "autoFocus" && (vr.hasOwnProperty(o) ? c != null && o === "onScroll" && b("scroll", e) : c != null && ls(e, o, c, i))
                        }
                    switch (n) {
                    case "input":
                        br(e),
                        wu(e, r, !1);
                        break;
                    case "textarea":
                        br(e),
                        ju(e);
                        break;
                    case "option":
                        r.value != null && e.setAttribute("value", "" + $t(r.value));
                        break;
                    case "select":
                        e.multiple = !!r.multiple,
                        o = r.value,
                        o != null ? Fn(e, !!r.multiple, o, !1) : r.defaultValue != null && Fn(e, !!r.multiple, r.defaultValue, !0);
                        break;
                    default:
                        typeof l.onClick == "function" && (e.onclick = Ol)
                    }
                    switch (n) {
                    case "button":
                    case "input":
                    case "select":
                    case "textarea":
                        r = !!r.autoFocus;
                        break e;
                    case "img":
                        r = !0;
                        break e;
                    default:
                        r = !1
                    }
                }
                r && (t.flags |= 4)
            }
            t.ref !== null && (t.flags |= 512,
            t.flags |= 2097152)
        }
        return ke(t),
        null;
    case 6:
        if (e && t.stateNode != null)
            Sd(e, t, e.memoizedProps, r);
        else {
            if (typeof r != "string" && t.stateNode === null)
                throw Error(w(166));
            if (n = bt(Pr.current),
            bt(ct.current),
            ul(t)) {
                if (r = t.stateNode,
                n = t.memoizedProps,
                r[ut] = t,
                (o = r.nodeValue !== n) && (e = We,
                e !== null))
                    switch (e.tag) {
                    case 3:
                        sl(r.nodeValue, n, (e.mode & 1) !== 0);
                        break;
                    case 5:
                        e.memoizedProps.suppressHydrationWarning !== !0 && sl(r.nodeValue, n, (e.mode & 1) !== 0)
                    }
                o && (t.flags |= 4)
            } else
                r = (n.nodeType === 9 ? n : n.ownerDocument).createTextNode(r),
                r[ut] = t,
                t.stateNode = r
        }
        return ke(t),
        null;
    case 13:
        if (ee(oe),
        r = t.memoizedState,
        e === null || e.memoizedState !== null && e.memoizedState.dehydrated !== null) {
            if (le && Ae !== null && t.mode & 1 && !(t.flags & 128))
                Ac(),
                Bn(),
                t.flags |= 98560,
                o = !1;
            else if (o = ul(t),
            r !== null && r.dehydrated !== null) {
                if (e === null) {
                    if (!o)
                        throw Error(w(318));
                    if (o = t.memoizedState,
                    o = o !== null ? o.dehydrated : null,
                    !o)
                        throw Error(w(317));
                    o[ut] = t
                } else
                    Bn(),
                    !(t.flags & 128) && (t.memoizedState = null),
                    t.flags |= 4;
                ke(t),
                o = !1
            } else
                be !== null && (Zi(be),
                be = null),
                o = !0;
            if (!o)
                return t.flags & 65536 ? t : null
        }
        return t.flags & 128 ? (t.lanes = n,
        t) : (r = r !== null,
        r !== (e !== null && e.memoizedState !== null) && r && (t.child.flags |= 8192,
        t.mode & 1 && (e === null || oe.current & 1 ? pe === 0 && (pe = 3) : Bs())),
        t.updateQueue !== null && (t.flags |= 4),
        ke(t),
        null);
    case 4:
        return Un(),
        Hi(e, t),
        e === null && zr(t.stateNode.containerInfo),
        ke(t),
        null;
    case 10:
        return Cs(t.type._context),
        ke(t),
        null;
    case 17:
        return De(t.type) && Ml(),
        ke(t),
        null;
    case 19:
        if (ee(oe),
        o = t.memoizedState,
        o === null)
            return ke(t),
            null;
        if (r = (t.flags & 128) !== 0,
        i = o.rendering,
        i === null)
            if (r)
                nr(o, !1);
            else {
                if (pe !== 0 || e !== null && e.flags & 128)
                    for (e = t.child; e !== null; ) {
                        if (i = Vl(e),
                        i !== null) {
                            for (t.flags |= 128,
                            nr(o, !1),
                            r = i.updateQueue,
                            r !== null && (t.updateQueue = r,
                            t.flags |= 4),
                            t.subtreeFlags = 0,
                            r = n,
                            n = t.child; n !== null; )
                                o = n,
                                e = r,
                                o.flags &= 14680066,
                                i = o.alternate,
                                i === null ? (o.childLanes = 0,
                                o.lanes = e,
                                o.child = null,
                                o.subtreeFlags = 0,
                                o.memoizedProps = null,
                                o.memoizedState = null,
                                o.updateQueue = null,
                                o.dependencies = null,
                                o.stateNode = null) : (o.childLanes = i.childLanes,
                                o.lanes = i.lanes,
                                o.child = i.child,
                                o.subtreeFlags = 0,
                                o.deletions = null,
                                o.memoizedProps = i.memoizedProps,
                                o.memoizedState = i.memoizedState,
                                o.updateQueue = i.updateQueue,
                                o.type = i.type,
                                e = i.dependencies,
                                o.dependencies = e === null ? null : {
                                    lanes: e.lanes,
                                    firstContext: e.firstContext
                                }),
                                n = n.sibling;
                            return q(oe, oe.current & 1 | 2),
                            t.child
                        }
                        e = e.sibling
                    }
                o.tail !== null && ae() > Vn && (t.flags |= 128,
                r = !0,
                nr(o, !1),
                t.lanes = 4194304)
            }
        else {
            if (!r)
                if (e = Vl(i),
                e !== null) {
                    if (t.flags |= 128,
                    r = !0,
                    n = e.updateQueue,
                    n !== null && (t.updateQueue = n,
                    t.flags |= 4),
                    nr(o, !0),
                    o.tail === null && o.tailMode === "hidden" && !i.alternate && !le)
                        return ke(t),
                        null
                } else
                    2 * ae() - o.renderingStartTime > Vn && n !== 1073741824 && (t.flags |= 128,
                    r = !0,
                    nr(o, !1),
                    t.lanes = 4194304);
            o.isBackwards ? (i.sibling = t.child,
            t.child = i) : (n = o.last,
            n !== null ? n.sibling = i : t.child = i,
            o.last = i)
        }
        return o.tail !== null ? (t = o.tail,
        o.rendering = t,
        o.tail = t.sibling,
        o.renderingStartTime = ae(),
        t.sibling = null,
        n = oe.current,
        q(oe, r ? n & 1 | 2 : n & 1),
        t) : (ke(t),
        null);
    case 22:
    case 23:
        return Ws(),
        r = t.memoizedState !== null,
        e !== null && e.memoizedState !== null !== r && (t.flags |= 8192),
        r && t.mode & 1 ? Me & 1073741824 && (ke(t),
        t.subtreeFlags & 6 && (t.flags |= 8192)) : ke(t),
        null;
    case 24:
        return null;
    case 25:
        return null
    }
    throw Error(w(156, t.tag))
}
function Ch(e, t) {
    switch (xs(t),
    t.tag) {
    case 1:
        return De(t.type) && Ml(),
        e = t.flags,
        e & 65536 ? (t.flags = e & -65537 | 128,
        t) : null;
    case 3:
        return Un(),
        ee(Re),
        ee(Ce),
        Ls(),
        e = t.flags,
        e & 65536 && !(e & 128) ? (t.flags = e & -65537 | 128,
        t) : null;
    case 5:
        return _s(t),
        null;
    case 13:
        if (ee(oe),
        e = t.memoizedState,
        e !== null && e.dehydrated !== null) {
            if (t.alternate === null)
                throw Error(w(340));
            Bn()
        }
        return e = t.flags,
        e & 65536 ? (t.flags = e & -65537 | 128,
        t) : null;
    case 19:
        return ee(oe),
        null;
    case 4:
        return Un(),
        null;
    case 10:
        return Cs(t.type._context),
        null;
    case 22:
    case 23:
        return Ws(),
        null;
    case 24:
        return null;
    default:
        return null
    }
}
var dl = !1
  , we = !1
  , jh = typeof WeakSet == "function" ? WeakSet : Set
  , N = null;
function Pn(e, t) {
    var n = e.ref;
    if (n !== null)
        if (typeof n == "function")
            try {
                n(null)
            } catch (r) {
                ue(e, t, r)
            }
        else
            n.current = null
}
function Vi(e, t, n) {
    try {
        n()
    } catch (r) {
        ue(e, t, r)
    }
}
var pa = !1;
function Eh(e, t) {
    if (_i = Il,
    e = Ec(),
    gs(e)) {
        if ("selectionStart"in e)
            var n = {
                start: e.selectionStart,
                end: e.selectionEnd
            };
        else
            e: {
                n = (n = e.ownerDocument) && n.defaultView || window;
                var r = n.getSelection && n.getSelection();
                if (r && r.rangeCount !== 0) {
                    n = r.anchorNode;
                    var l = r.anchorOffset
                      , o = r.focusNode;
                    r = r.focusOffset;
                    try {
                        n.nodeType,
                        o.nodeType
                    } catch {
                        n = null;
                        break e
                    }
                    var i = 0
                      , u = -1
                      , c = -1
                      , f = 0
                      , v = 0
                      , g = e
                      , y = null;
                    t: for (; ; ) {
                        for (var C; g !== n || l !== 0 && g.nodeType !== 3 || (u = i + l),
                        g !== o || r !== 0 && g.nodeType !== 3 || (c = i + r),
                        g.nodeType === 3 && (i += g.nodeValue.length),
                        (C = g.firstChild) !== null; )
                            y = g,
                            g = C;
                        for (; ; ) {
                            if (g === e)
                                break t;
                            if (y === n && ++f === l && (u = i),
                            y === o && ++v === r && (c = i),
                            (C = g.nextSibling) !== null)
                                break;
                            g = y,
                            y = g.parentNode
                        }
                        g = C
                    }
                    n = u === -1 || c === -1 ? null : {
                        start: u,
                        end: c
                    }
                } else
                    n = null
            }
        n = n || {
            start: 0,
            end: 0
        }
    } else
        n = null;
    for (Li = {
        focusedElem: e,
        selectionRange: n
    },
    Il = !1,
    N = t; N !== null; )
        if (t = N,
        e = t.child,
        (t.subtreeFlags & 1028) !== 0 && e !== null)
            e.return = t,
            N = e;
        else
            for (; N !== null; ) {
                t = N;
                try {
                    var j = t.alternate;
                    if (t.flags & 1024)
                        switch (t.tag) {
                        case 0:
                        case 11:
                        case 15:
                            break;
                        case 1:
                            if (j !== null) {
                                var _ = j.memoizedProps
                                  , Z = j.memoizedState
                                  , p = t.stateNode
                                  , d = p.getSnapshotBeforeUpdate(t.elementType === t.type ? _ : Ze(t.type, _), Z);
                                p.__reactInternalSnapshotBeforeUpdate = d
                            }
                            break;
                        case 3:
                            var m = t.stateNode.containerInfo;
                            m.nodeType === 1 ? m.textContent = "" : m.nodeType === 9 && m.documentElement && m.removeChild(m.documentElement);
                            break;
                        case 5:
                        case 6:
                        case 4:
                        case 17:
                            break;
                        default:
                            throw Error(w(163))
                        }
                } catch (S) {
                    ue(t, t.return, S)
                }
                if (e = t.sibling,
                e !== null) {
                    e.return = t.return,
                    N = e;
                    break
                }
                N = t.return
            }
    return j = pa,
    pa = !1,
    j
}
function mr(e, t, n) {
    var r = t.updateQueue;
    if (r = r !== null ? r.lastEffect : null,
    r !== null) {
        var l = r = r.next;
        do {
            if ((l.tag & e) === e) {
                var o = l.destroy;
                l.destroy = void 0,
                o !== void 0 && Vi(t, n, o)
            }
            l = l.next
        } while (l !== r)
    }
}
function so(e, t) {
    if (t = t.updateQueue,
    t = t !== null ? t.lastEffect : null,
    t !== null) {
        var n = t = t.next;
        do {
            if ((n.tag & e) === e) {
                var r = n.create;
                n.destroy = r()
            }
            n = n.next
        } while (n !== t)
    }
}
function Qi(e) {
    var t = e.ref;
    if (t !== null) {
        var n = e.stateNode;
        switch (e.tag) {
        case 5:
            e = n;
            break;
        default:
            e = n
        }
        typeof t == "function" ? t(e) : t.current = e
    }
}
function kd(e) {
    var t = e.alternate;
    t !== null && (e.alternate = null,
    kd(t)),
    e.child = null,
    e.deletions = null,
    e.sibling = null,
    e.tag === 5 && (t = e.stateNode,
    t !== null && (delete t[ut],
    delete t[Lr],
    delete t[Ni],
    delete t[sh],
    delete t[uh])),
    e.stateNode = null,
    e.return = null,
    e.dependencies = null,
    e.memoizedProps = null,
    e.memoizedState = null,
    e.pendingProps = null,
    e.stateNode = null,
    e.updateQueue = null
}
function wd(e) {
    return e.tag === 5 || e.tag === 3 || e.tag === 4
}
function ha(e) {
    e: for (; ; ) {
        for (; e.sibling === null; ) {
            if (e.return === null || wd(e.return))
                return null;
            e = e.return
        }
        for (e.sibling.return = e.return,
        e = e.sibling; e.tag !== 5 && e.tag !== 6 && e.tag !== 18; ) {
            if (e.flags & 2 || e.child === null || e.tag === 4)
                continue e;
            e.child.return = e,
            e = e.child
        }
        if (!(e.flags & 2))
            return e.stateNode
    }
}
function Ki(e, t, n) {
    var r = e.tag;
    if (r === 5 || r === 6)
        e = e.stateNode,
        t ? n.nodeType === 8 ? n.parentNode.insertBefore(e, t) : n.insertBefore(e, t) : (n.nodeType === 8 ? (t = n.parentNode,
        t.insertBefore(e, n)) : (t = n,
        t.appendChild(e)),
        n = n._reactRootContainer,
        n != null || t.onclick !== null || (t.onclick = Ol));
    else if (r !== 4 && (e = e.child,
    e !== null))
        for (Ki(e, t, n),
        e = e.sibling; e !== null; )
            Ki(e, t, n),
            e = e.sibling
}
function Yi(e, t, n) {
    var r = e.tag;
    if (r === 5 || r === 6)
        e = e.stateNode,
        t ? n.insertBefore(e, t) : n.appendChild(e);
    else if (r !== 4 && (e = e.child,
    e !== null))
        for (Yi(e, t, n),
        e = e.sibling; e !== null; )
            Yi(e, t, n),
            e = e.sibling
}
var ye = null
  , qe = !1;
function zt(e, t, n) {
    for (n = n.child; n !== null; )
        Cd(e, t, n),
        n = n.sibling
}
function Cd(e, t, n) {
    if (at && typeof at.onCommitFiberUnmount == "function")
        try {
            at.onCommitFiberUnmount(bl, n)
        } catch {}
    switch (n.tag) {
    case 5:
        we || Pn(n, t);
    case 6:
        var r = ye
          , l = qe;
        ye = null,
        zt(e, t, n),
        ye = r,
        qe = l,
        ye !== null && (qe ? (e = ye,
        n = n.stateNode,
        e.nodeType === 8 ? e.parentNode.removeChild(n) : e.removeChild(n)) : ye.removeChild(n.stateNode));
        break;
    case 18:
        ye !== null && (qe ? (e = ye,
        n = n.stateNode,
        e.nodeType === 8 ? Vo(e.parentNode, n) : e.nodeType === 1 && Vo(e, n),
        Cr(e)) : Vo(ye, n.stateNode));
        break;
    case 4:
        r = ye,
        l = qe,
        ye = n.stateNode.containerInfo,
        qe = !0,
        zt(e, t, n),
        ye = r,
        qe = l;
        break;
    case 0:
    case 11:
    case 14:
    case 15:
        if (!we && (r = n.updateQueue,
        r !== null && (r = r.lastEffect,
        r !== null))) {
            l = r = r.next;
            do {
                var o = l
                  , i = o.destroy;
                o = o.tag,
                i !== void 0 && (o & 2 || o & 4) && Vi(n, t, i),
                l = l.next
            } while (l !== r)
        }
        zt(e, t, n);
        break;
    case 1:
        if (!we && (Pn(n, t),
        r = n.stateNode,
        typeof r.componentWillUnmount == "function"))
            try {
                r.props = n.memoizedProps,
                r.state = n.memoizedState,
                r.componentWillUnmount()
            } catch (u) {
                ue(n, t, u)
            }
        zt(e, t, n);
        break;
    case 21:
        zt(e, t, n);
        break;
    case 22:
        n.mode & 1 ? (we = (r = we) || n.memoizedState !== null,
        zt(e, t, n),
        we = r) : zt(e, t, n);
        break;
    default:
        zt(e, t, n)
    }
}
function ma(e) {
    var t = e.updateQueue;
    if (t !== null) {
        e.updateQueue = null;
        var n = e.stateNode;
        n === null && (n = e.stateNode = new jh),
        t.forEach(function(r) {
            var l = Rh.bind(null, e, r);
            n.has(r) || (n.add(r),
            r.then(l, l))
        })
    }
}
function Je(e, t) {
    var n = t.deletions;
    if (n !== null)
        for (var r = 0; r < n.length; r++) {
            var l = n[r];
            try {
                var o = e
                  , i = t
                  , u = i;
                e: for (; u !== null; ) {
                    switch (u.tag) {
                    case 5:
                        ye = u.stateNode,
                        qe = !1;
                        break e;
                    case 3:
                        ye = u.stateNode.containerInfo,
                        qe = !0;
                        break e;
                    case 4:
                        ye = u.stateNode.containerInfo,
                        qe = !0;
                        break e
                    }
                    u = u.return
                }
                if (ye === null)
                    throw Error(w(160));
                Cd(o, i, l),
                ye = null,
                qe = !1;
                var c = l.alternate;
                c !== null && (c.return = null),
                l.return = null
            } catch (f) {
                ue(l, t, f)
            }
        }
    if (t.subtreeFlags & 12854)
        for (t = t.child; t !== null; )
            jd(t, e),
            t = t.sibling
}
function jd(e, t) {
    var n = e.alternate
      , r = e.flags;
    switch (e.tag) {
    case 0:
    case 11:
    case 14:
    case 15:
        if (Je(t, e),
        it(e),
        r & 4) {
            try {
                mr(3, e, e.return),
                so(3, e)
            } catch (_) {
                ue(e, e.return, _)
            }
            try {
                mr(5, e, e.return)
            } catch (_) {
                ue(e, e.return, _)
            }
        }
        break;
    case 1:
        Je(t, e),
        it(e),
        r & 512 && n !== null && Pn(n, n.return);
        break;
    case 5:
        if (Je(t, e),
        it(e),
        r & 512 && n !== null && Pn(n, n.return),
        e.flags & 32) {
            var l = e.stateNode;
            try {
                xr(l, "")
            } catch (_) {
                ue(e, e.return, _)
            }
        }
        if (r & 4 && (l = e.stateNode,
        l != null)) {
            var o = e.memoizedProps
              , i = n !== null ? n.memoizedProps : o
              , u = e.type
              , c = e.updateQueue;
            if (e.updateQueue = null,
            c !== null)
                try {
                    u === "input" && o.type === "radio" && o.name != null && Ka(l, o),
                    gi(u, i);
                    var f = gi(u, o);
                    for (i = 0; i < c.length; i += 2) {
                        var v = c[i]
                          , g = c[i + 1];
                        v === "style" ? Za(l, g) : v === "dangerouslySetInnerHTML" ? Ga(l, g) : v === "children" ? xr(l, g) : ls(l, v, g, f)
                    }
                    switch (u) {
                    case "input":
                        fi(l, o);
                        break;
                    case "textarea":
                        Ya(l, o);
                        break;
                    case "select":
                        var y = l._wrapperState.wasMultiple;
                        l._wrapperState.wasMultiple = !!o.multiple;
                        var C = o.value;
                        C != null ? Fn(l, !!o.multiple, C, !1) : y !== !!o.multiple && (o.defaultValue != null ? Fn(l, !!o.multiple, o.defaultValue, !0) : Fn(l, !!o.multiple, o.multiple ? [] : "", !1))
                    }
                    l[Lr] = o
                } catch (_) {
                    ue(e, e.return, _)
                }
        }
        break;
    case 6:
        if (Je(t, e),
        it(e),
        r & 4) {
            if (e.stateNode === null)
                throw Error(w(162));
            l = e.stateNode,
            o = e.memoizedProps;
            try {
                l.nodeValue = o
            } catch (_) {
                ue(e, e.return, _)
            }
        }
        break;
    case 3:
        if (Je(t, e),
        it(e),
        r & 4 && n !== null && n.memoizedState.isDehydrated)
            try {
                Cr(t.containerInfo)
            } catch (_) {
                ue(e, e.return, _)
            }
        break;
    case 4:
        Je(t, e),
        it(e);
        break;
    case 13:
        Je(t, e),
        it(e),
        l = e.child,
        l.flags & 8192 && (o = l.memoizedState !== null,
        l.stateNode.isHidden = o,
        !o || l.alternate !== null && l.alternate.memoizedState !== null || (Ms = ae())),
        r & 4 && ma(e);
        break;
    case 22:
        if (v = n !== null && n.memoizedState !== null,
        e.mode & 1 ? (we = (f = we) || v,
        Je(t, e),
        we = f) : Je(t, e),
        it(e),
        r & 8192) {
            if (f = e.memoizedState !== null,
            (e.stateNode.isHidden = f) && !v && e.mode & 1)
                for (N = e,
                v = e.child; v !== null; ) {
                    for (g = N = v; N !== null; ) {
                        switch (y = N,
                        C = y.child,
                        y.tag) {
                        case 0:
                        case 11:
                        case 14:
                        case 15:
                            mr(4, y, y.return);
                            break;
                        case 1:
                            Pn(y, y.return);
                            var j = y.stateNode;
                            if (typeof j.componentWillUnmount == "function") {
                                r = y,
                                n = y.return;
                                try {
                                    t = r,
                                    j.props = t.memoizedProps,
                                    j.state = t.memoizedState,
                                    j.componentWillUnmount()
                                } catch (_) {
                                    ue(r, n, _)
                                }
                            }
                            break;
                        case 5:
                            Pn(y, y.return);
                            break;
                        case 22:
                            if (y.memoizedState !== null) {
                                ga(g);
                                continue
                            }
                        }
                        C !== null ? (C.return = y,
                        N = C) : ga(g)
                    }
                    v = v.sibling
                }
            e: for (v = null,
            g = e; ; ) {
                if (g.tag === 5) {
                    if (v === null) {
                        v = g;
                        try {
                            l = g.stateNode,
                            f ? (o = l.style,
                            typeof o.setProperty == "function" ? o.setProperty("display", "none", "important") : o.display = "none") : (u = g.stateNode,
                            c = g.memoizedProps.style,
                            i = c != null && c.hasOwnProperty("display") ? c.display : null,
                            u.style.display = Ja("display", i))
                        } catch (_) {
                            ue(e, e.return, _)
                        }
                    }
                } else if (g.tag === 6) {
                    if (v === null)
                        try {
                            g.stateNode.nodeValue = f ? "" : g.memoizedProps
                        } catch (_) {
                            ue(e, e.return, _)
                        }
                } else if ((g.tag !== 22 && g.tag !== 23 || g.memoizedState === null || g === e) && g.child !== null) {
                    g.child.return = g,
                    g = g.child;
                    continue
                }
                if (g === e)
                    break e;
                for (; g.sibling === null; ) {
                    if (g.return === null || g.return === e)
                        break e;
                    v === g && (v = null),
                    g = g.return
                }
                v === g && (v = null),
                g.sibling.return = g.return,
                g = g.sibling
            }
        }
        break;
    case 19:
        Je(t, e),
        it(e),
        r & 4 && ma(e);
        break;
    case 21:
        break;
    default:
        Je(t, e),
        it(e)
    }
}
function it(e) {
    var t = e.flags;
    if (t & 2) {
        try {
            e: {
                for (var n = e.return; n !== null; ) {
                    if (wd(n)) {
                        var r = n;
                        break e
                    }
                    n = n.return
                }
                throw Error(w(160))
            }
            switch (r.tag) {
            case 5:
                var l = r.stateNode;
                r.flags & 32 && (xr(l, ""),
                r.flags &= -33);
                var o = ha(e);
                Yi(e, o, l);
                break;
            case 3:
            case 4:
                var i = r.stateNode.containerInfo
                  , u = ha(e);
                Ki(e, u, i);
                break;
            default:
                throw Error(w(161))
            }
        } catch (c) {
            ue(e, e.return, c)
        }
        e.flags &= -3
    }
    t & 4096 && (e.flags &= -4097)
}
function zh(e, t, n) {
    N = e,
    Ed(e)
}
function Ed(e, t, n) {
    for (var r = (e.mode & 1) !== 0; N !== null; ) {
        var l = N
          , o = l.child;
        if (l.tag === 22 && r) {
            var i = l.memoizedState !== null || dl;
            if (!i) {
                var u = l.alternate
                  , c = u !== null && u.memoizedState !== null || we;
                u = dl;
                var f = we;
                if (dl = i,
                (we = c) && !f)
                    for (N = l; N !== null; )
                        i = N,
                        c = i.child,
                        i.tag === 22 && i.memoizedState !== null ? va(l) : c !== null ? (c.return = i,
                        N = c) : va(l);
                for (; o !== null; )
                    N = o,
                    Ed(o),
                    o = o.sibling;
                N = l,
                dl = u,
                we = f
            }
            ya(e)
        } else
            l.subtreeFlags & 8772 && o !== null ? (o.return = l,
            N = o) : ya(e)
    }
}
function ya(e) {
    for (; N !== null; ) {
        var t = N;
        if (t.flags & 8772) {
            var n = t.alternate;
            try {
                if (t.flags & 8772)
                    switch (t.tag) {
                    case 0:
                    case 11:
                    case 15:
                        we || so(5, t);
                        break;
                    case 1:
                        var r = t.stateNode;
                        if (t.flags & 4 && !we)
                            if (n === null)
                                r.componentDidMount();
                            else {
                                var l = t.elementType === t.type ? n.memoizedProps : Ze(t.type, n.memoizedProps);
                                r.componentDidUpdate(l, n.memoizedState, r.__reactInternalSnapshotBeforeUpdate)
                            }
                        var o = t.updateQueue;
                        o !== null && ea(t, o, r);
                        break;
                    case 3:
                        var i = t.updateQueue;
                        if (i !== null) {
                            if (n = null,
                            t.child !== null)
                                switch (t.child.tag) {
                                case 5:
                                    n = t.child.stateNode;
                                    break;
                                case 1:
                                    n = t.child.stateNode
                                }
                            ea(t, i, n)
                        }
                        break;
                    case 5:
                        var u = t.stateNode;
                        if (n === null && t.flags & 4) {
                            n = u;
                            var c = t.memoizedProps;
                            switch (t.type) {
                            case "button":
                            case "input":
                            case "select":
                            case "textarea":
                                c.autoFocus && n.focus();
                                break;
                            case "img":
                                c.src && (n.src = c.src)
                            }
                        }
                        break;
                    case 6:
                        break;
                    case 4:
                        break;
                    case 12:
                        break;
                    case 13:
                        if (t.memoizedState === null) {
                            var f = t.alternate;
                            if (f !== null) {
                                var v = f.memoizedState;
                                if (v !== null) {
                                    var g = v.dehydrated;
                                    g !== null && Cr(g)
                                }
                            }
                        }
                        break;
                    case 19:
                    case 17:
                    case 21:
                    case 22:
                    case 23:
                    case 25:
                        break;
                    default:
                        throw Error(w(163))
                    }
                we || t.flags & 512 && Qi(t)
            } catch (y) {
                ue(t, t.return, y)
            }
        }
        if (t === e) {
            N = null;
            break
        }
        if (n = t.sibling,
        n !== null) {
            n.return = t.return,
            N = n;
            break
        }
        N = t.return
    }
}
function ga(e) {
    for (; N !== null; ) {
        var t = N;
        if (t === e) {
            N = null;
            break
        }
        var n = t.sibling;
        if (n !== null) {
            n.return = t.return,
            N = n;
            break
        }
        N = t.return
    }
}
function va(e) {
    for (; N !== null; ) {
        var t = N;
        try {
            switch (t.tag) {
            case 0:
            case 11:
            case 15:
                var n = t.return;
                try {
                    so(4, t)
                } catch (c) {
                    ue(t, n, c)
                }
                break;
            case 1:
                var r = t.stateNode;
                if (typeof r.componentDidMount == "function") {
                    var l = t.return;
                    try {
                        r.componentDidMount()
                    } catch (c) {
                        ue(t, l, c)
                    }
                }
                var o = t.return;
                try {
                    Qi(t)
                } catch (c) {
                    ue(t, o, c)
                }
                break;
            case 5:
                var i = t.return;
                try {
                    Qi(t)
                } catch (c) {
                    ue(t, i, c)
                }
            }
        } catch (c) {
            ue(t, t.return, c)
        }
        if (t === e) {
            N = null;
            break
        }
        var u = t.sibling;
        if (u !== null) {
            u.return = t.return,
            N = u;
            break
        }
        N = t.return
    }
}
var _h = Math.ceil
  , Yl = wt.ReactCurrentDispatcher
  , Ds = wt.ReactCurrentOwner
  , Ye = wt.ReactCurrentBatchConfig
  , Y = 0
  , me = null
  , de = null
  , ge = 0
  , Me = 0
  , Nn = Vt(0)
  , pe = 0
  , Rr = null
  , sn = 0
  , uo = 0
  , Os = 0
  , yr = null
  , Ne = null
  , Ms = 0
  , Vn = 1 / 0
  , pt = null
  , Xl = !1
  , Xi = null
  , At = null
  , fl = !1
  , Ft = null
  , Gl = 0
  , gr = 0
  , Gi = null
  , El = -1
  , zl = 0;
function _e() {
    return Y & 6 ? ae() : El !== -1 ? El : El = ae()
}
function Wt(e) {
    return e.mode & 1 ? Y & 2 && ge !== 0 ? ge & -ge : ch.transition !== null ? (zl === 0 && (zl = ac()),
    zl) : (e = G,
    e !== 0 || (e = window.event,
    e = e === void 0 ? 16 : yc(e.type)),
    e) : 1
}
function tt(e, t, n, r) {
    if (50 < gr)
        throw gr = 0,
        Gi = null,
        Error(w(185));
    Or(e, n, r),
    (!(Y & 2) || e !== me) && (e === me && (!(Y & 2) && (uo |= n),
    pe === 4 && Pt(e, ge)),
    Oe(e, r),
    n === 1 && Y === 0 && !(t.mode & 1) && (Vn = ae() + 500,
    lo && Qt()))
}
function Oe(e, t) {
    var n = e.callbackNode;
    cp(e, t);
    var r = Fl(e, e === me ? ge : 0);
    if (r === 0)
        n !== null && _u(n),
        e.callbackNode = null,
        e.callbackPriority = 0;
    else if (t = r & -r,
    e.callbackPriority !== t) {
        if (n != null && _u(n),
        t === 1)
            e.tag === 0 ? ah(xa.bind(null, e)) : Dc(xa.bind(null, e)),
            oh(function() {
                !(Y & 6) && Qt()
            }),
            n = null;
        else {
            switch (cc(r)) {
            case 1:
                n = as;
                break;
            case 4:
                n = sc;
                break;
            case 16:
                n = Nl;
                break;
            case 536870912:
                n = uc;
                break;
            default:
                n = Nl
            }
            n = Id(n, zd.bind(null, e))
        }
        e.callbackPriority = t,
        e.callbackNode = n
    }
}
function zd(e, t) {
    if (El = -1,
    zl = 0,
    Y & 6)
        throw Error(w(327));
    var n = e.callbackNode;
    if (Mn() && e.callbackNode !== n)
        return null;
    var r = Fl(e, e === me ? ge : 0);
    if (r === 0)
        return null;
    if (r & 30 || r & e.expiredLanes || t)
        t = Jl(e, r);
    else {
        t = r;
        var l = Y;
        Y |= 2;
        var o = Ld();
        (me !== e || ge !== t) && (pt = null,
        Vn = ae() + 500,
        en(e, t));
        do
            try {
                Ph();
                break
            } catch (u) {
                _d(e, u)
            }
        while (!0);
        ws(),
        Yl.current = o,
        Y = l,
        de !== null ? t = 0 : (me = null,
        ge = 0,
        t = pe)
    }
    if (t !== 0) {
        if (t === 2 && (l = wi(e),
        l !== 0 && (r = l,
        t = Ji(e, l))),
        t === 1)
            throw n = Rr,
            en(e, 0),
            Pt(e, r),
            Oe(e, ae()),
            n;
        if (t === 6)
            Pt(e, r);
        else {
            if (l = e.current.alternate,
            !(r & 30) && !Lh(l) && (t = Jl(e, r),
            t === 2 && (o = wi(e),
            o !== 0 && (r = o,
            t = Ji(e, o))),
            t === 1))
                throw n = Rr,
                en(e, 0),
                Pt(e, r),
                Oe(e, ae()),
                n;
            switch (e.finishedWork = l,
            e.finishedLanes = r,
            t) {
            case 0:
            case 1:
                throw Error(w(345));
            case 2:
                Jt(e, Ne, pt);
                break;
            case 3:
                if (Pt(e, r),
                (r & 130023424) === r && (t = Ms + 500 - ae(),
                10 < t)) {
                    if (Fl(e, 0) !== 0)
                        break;
                    if (l = e.suspendedLanes,
                    (l & r) !== r) {
                        _e(),
                        e.pingedLanes |= e.suspendedLanes & l;
                        break
                    }
                    e.timeoutHandle = Pi(Jt.bind(null, e, Ne, pt), t);
                    break
                }
                Jt(e, Ne, pt);
                break;
            case 4:
                if (Pt(e, r),
                (r & 4194240) === r)
                    break;
                for (t = e.eventTimes,
                l = -1; 0 < r; ) {
                    var i = 31 - et(r);
                    o = 1 << i,
                    i = t[i],
                    i > l && (l = i),
                    r &= ~o
                }
                if (r = l,
                r = ae() - r,
                r = (120 > r ? 120 : 480 > r ? 480 : 1080 > r ? 1080 : 1920 > r ? 1920 : 3e3 > r ? 3e3 : 4320 > r ? 4320 : 1960 * _h(r / 1960)) - r,
                10 < r) {
                    e.timeoutHandle = Pi(Jt.bind(null, e, Ne, pt), r);
                    break
                }
                Jt(e, Ne, pt);
                break;
            case 5:
                Jt(e, Ne, pt);
                break;
            default:
                throw Error(w(329))
            }
        }
    }
    return Oe(e, ae()),
    e.callbackNode === n ? zd.bind(null, e) : null
}
function Ji(e, t) {
    var n = yr;
    return e.current.memoizedState.isDehydrated && (en(e, t).flags |= 256),
    e = Jl(e, t),
    e !== 2 && (t = Ne,
    Ne = n,
    t !== null && Zi(t)),
    e
}
function Zi(e) {
    Ne === null ? Ne = e : Ne.push.apply(Ne, e)
}
function Lh(e) {
    for (var t = e; ; ) {
        if (t.flags & 16384) {
            var n = t.updateQueue;
            if (n !== null && (n = n.stores,
            n !== null))
                for (var r = 0; r < n.length; r++) {
                    var l = n[r]
                      , o = l.getSnapshot;
                    l = l.value;
                    try {
                        if (!nt(o(), l))
                            return !1
                    } catch {
                        return !1
                    }
                }
        }
        if (n = t.child,
        t.subtreeFlags & 16384 && n !== null)
            n.return = t,
            t = n;
        else {
            if (t === e)
                break;
            for (; t.sibling === null; ) {
                if (t.return === null || t.return === e)
                    return !0;
                t = t.return
            }
            t.sibling.return = t.return,
            t = t.sibling
        }
    }
    return !0
}
function Pt(e, t) {
    for (t &= ~Os,
    t &= ~uo,
    e.suspendedLanes |= t,
    e.pingedLanes &= ~t,
    e = e.expirationTimes; 0 < t; ) {
        var n = 31 - et(t)
          , r = 1 << n;
        e[n] = -1,
        t &= ~r
    }
}
function xa(e) {
    if (Y & 6)
        throw Error(w(327));
    Mn();
    var t = Fl(e, 0);
    if (!(t & 1))
        return Oe(e, ae()),
        null;
    var n = Jl(e, t);
    if (e.tag !== 0 && n === 2) {
        var r = wi(e);
        r !== 0 && (t = r,
        n = Ji(e, r))
    }
    if (n === 1)
        throw n = Rr,
        en(e, 0),
        Pt(e, t),
        Oe(e, ae()),
        n;
    if (n === 6)
        throw Error(w(345));
    return e.finishedWork = e.current.alternate,
    e.finishedLanes = t,
    Jt(e, Ne, pt),
    Oe(e, ae()),
    null
}
function As(e, t) {
    var n = Y;
    Y |= 1;
    try {
        return e(t)
    } finally {
        Y = n,
        Y === 0 && (Vn = ae() + 500,
        lo && Qt())
    }
}
function un(e) {
    Ft !== null && Ft.tag === 0 && !(Y & 6) && Mn();
    var t = Y;
    Y |= 1;
    var n = Ye.transition
      , r = G;
    try {
        if (Ye.transition = null,
        G = 1,
        e)
            return e()
    } finally {
        G = r,
        Ye.transition = n,
        Y = t,
        !(Y & 6) && Qt()
    }
}
function Ws() {
    Me = Nn.current,
    ee(Nn)
}
function en(e, t) {
    e.finishedWork = null,
    e.finishedLanes = 0;
    var n = e.timeoutHandle;
    if (n !== -1 && (e.timeoutHandle = -1,
    lh(n)),
    de !== null)
        for (n = de.return; n !== null; ) {
            var r = n;
            switch (xs(r),
            r.tag) {
            case 1:
                r = r.type.childContextTypes,
                r != null && Ml();
                break;
            case 3:
                Un(),
                ee(Re),
                ee(Ce),
                Ls();
                break;
            case 5:
                _s(r);
                break;
            case 4:
                Un();
                break;
            case 13:
                ee(oe);
                break;
            case 19:
                ee(oe);
                break;
            case 10:
                Cs(r.type._context);
                break;
            case 22:
            case 23:
                Ws()
            }
            n = n.return
        }
    if (me = e,
    de = e = Bt(e.current, null),
    ge = Me = t,
    pe = 0,
    Rr = null,
    Os = uo = sn = 0,
    Ne = yr = null,
    qt !== null) {
        for (t = 0; t < qt.length; t++)
            if (n = qt[t],
            r = n.interleaved,
            r !== null) {
                n.interleaved = null;
                var l = r.next
                  , o = n.pending;
                if (o !== null) {
                    var i = o.next;
                    o.next = l,
                    r.next = i
                }
                n.pending = r
            }
        qt = null
    }
    return e
}
function _d(e, t) {
    do {
        var n = de;
        try {
            if (ws(),
            wl.current = Kl,
            Ql) {
                for (var r = ie.memoizedState; r !== null; ) {
                    var l = r.queue;
                    l !== null && (l.pending = null),
                    r = r.next
                }
                Ql = !1
            }
            if (on = 0,
            he = fe = ie = null,
            hr = !1,
            Nr = 0,
            Ds.current = null,
            n === null || n.return === null) {
                pe = 1,
                Rr = t,
                de = null;
                break
            }
            e: {
                var o = e
                  , i = n.return
                  , u = n
                  , c = t;
                if (t = ge,
                u.flags |= 32768,
                c !== null && typeof c == "object" && typeof c.then == "function") {
                    var f = c
                      , v = u
                      , g = v.tag;
                    if (!(v.mode & 1) && (g === 0 || g === 11 || g === 15)) {
                        var y = v.alternate;
                        y ? (v.updateQueue = y.updateQueue,
                        v.memoizedState = y.memoizedState,
                        v.lanes = y.lanes) : (v.updateQueue = null,
                        v.memoizedState = null)
                    }
                    var C = ia(i);
                    if (C !== null) {
                        C.flags &= -257,
                        sa(C, i, u, o, t),
                        C.mode & 1 && oa(o, f, t),
                        t = C,
                        c = f;
                        var j = t.updateQueue;
                        if (j === null) {
                            var _ = new Set;
                            _.add(c),
                            t.updateQueue = _
                        } else
                            j.add(c);
                        break e
                    } else {
                        if (!(t & 1)) {
                            oa(o, f, t),
                            Bs();
                            break e
                        }
                        c = Error(w(426))
                    }
                } else if (le && u.mode & 1) {
                    var Z = ia(i);
                    if (Z !== null) {
                        !(Z.flags & 65536) && (Z.flags |= 256),
                        sa(Z, i, u, o, t),
                        Ss(Hn(c, u));
                        break e
                    }
                }
                o = c = Hn(c, u),
                pe !== 4 && (pe = 2),
                yr === null ? yr = [o] : yr.push(o),
                o = i;
                do {
                    switch (o.tag) {
                    case 3:
                        o.flags |= 65536,
                        t &= -t,
                        o.lanes |= t;
                        var p = cd(o, c, t);
                        bu(o, p);
                        break e;
                    case 1:
                        u = c;
                        var d = o.type
                          , m = o.stateNode;
                        if (!(o.flags & 128) && (typeof d.getDerivedStateFromError == "function" || m !== null && typeof m.componentDidCatch == "function" && (At === null || !At.has(m)))) {
                            o.flags |= 65536,
                            t &= -t,
                            o.lanes |= t;
                            var S = dd(o, u, t);
                            bu(o, S);
                            break e
                        }
                    }
                    o = o.return
                } while (o !== null)
            }
            Pd(n)
        } catch (E) {
            t = E,
            de === n && n !== null && (de = n = n.return);
            continue
        }
        break
    } while (!0)
}
function Ld() {
    var e = Yl.current;
    return Yl.current = Kl,
    e === null ? Kl : e
}
function Bs() {
    (pe === 0 || pe === 3 || pe === 2) && (pe = 4),
    me === null || !(sn & 268435455) && !(uo & 268435455) || Pt(me, ge)
}
function Jl(e, t) {
    var n = Y;
    Y |= 2;
    var r = Ld();
    (me !== e || ge !== t) && (pt = null,
    en(e, t));
    do
        try {
            Th();
            break
        } catch (l) {
            _d(e, l)
        }
    while (!0);
    if (ws(),
    Y = n,
    Yl.current = r,
    de !== null)
        throw Error(w(261));
    return me = null,
    ge = 0,
    pe
}
function Th() {
    for (; de !== null; )
        Td(de)
}
function Ph() {
    for (; de !== null && !tp(); )
        Td(de)
}
function Td(e) {
    var t = Fd(e.alternate, e, Me);
    e.memoizedProps = e.pendingProps,
    t === null ? Pd(e) : de = t,
    Ds.current = null
}
function Pd(e) {
    var t = e;
    do {
        var n = t.alternate;
        if (e = t.return,
        t.flags & 32768) {
            if (n = Ch(n, t),
            n !== null) {
                n.flags &= 32767,
                de = n;
                return
            }
            if (e !== null)
                e.flags |= 32768,
                e.subtreeFlags = 0,
                e.deletions = null;
            else {
                pe = 6,
                de = null;
                return
            }
        } else if (n = wh(n, t, Me),
        n !== null) {
            de = n;
            return
        }
        if (t = t.sibling,
        t !== null) {
            de = t;
            return
        }
        de = t = e
    } while (t !== null);
    pe === 0 && (pe = 5)
}
function Jt(e, t, n) {
    var r = G
      , l = Ye.transition;
    try {
        Ye.transition = null,
        G = 1,
        Nh(e, t, n, r)
    } finally {
        Ye.transition = l,
        G = r
    }
    return null
}
function Nh(e, t, n, r) {
    do
        Mn();
    while (Ft !== null);
    if (Y & 6)
        throw Error(w(327));
    n = e.finishedWork;
    var l = e.finishedLanes;
    if (n === null)
        return null;
    if (e.finishedWork = null,
    e.finishedLanes = 0,
    n === e.current)
        throw Error(w(177));
    e.callbackNode = null,
    e.callbackPriority = 0;
    var o = n.lanes | n.childLanes;
    if (dp(e, o),
    e === me && (de = me = null,
    ge = 0),
    !(n.subtreeFlags & 2064) && !(n.flags & 2064) || fl || (fl = !0,
    Id(Nl, function() {
        return Mn(),
        null
    })),
    o = (n.flags & 15990) !== 0,
    n.subtreeFlags & 15990 || o) {
        o = Ye.transition,
        Ye.transition = null;
        var i = G;
        G = 1;
        var u = Y;
        Y |= 4,
        Ds.current = null,
        Eh(e, n),
        jd(n, e),
        Zp(Li),
        Il = !!_i,
        Li = _i = null,
        e.current = n,
        zh(n),
        np(),
        Y = u,
        G = i,
        Ye.transition = o
    } else
        e.current = n;
    if (fl && (fl = !1,
    Ft = e,
    Gl = l),
    o = e.pendingLanes,
    o === 0 && (At = null),
    op(n.stateNode),
    Oe(e, ae()),
    t !== null)
        for (r = e.onRecoverableError,
        n = 0; n < t.length; n++)
            l = t[n],
            r(l.value, {
                componentStack: l.stack,
                digest: l.digest
            });
    if (Xl)
        throw Xl = !1,
        e = Xi,
        Xi = null,
        e;
    return Gl & 1 && e.tag !== 0 && Mn(),
    o = e.pendingLanes,
    o & 1 ? e === Gi ? gr++ : (gr = 0,
    Gi = e) : gr = 0,
    Qt(),
    null
}
function Mn() {
    if (Ft !== null) {
        var e = cc(Gl)
          , t = Ye.transition
          , n = G;
        try {
            if (Ye.transition = null,
            G = 16 > e ? 16 : e,
            Ft === null)
                var r = !1;
            else {
                if (e = Ft,
                Ft = null,
                Gl = 0,
                Y & 6)
                    throw Error(w(331));
                var l = Y;
                for (Y |= 4,
                N = e.current; N !== null; ) {
                    var o = N
                      , i = o.child;
                    if (N.flags & 16) {
                        var u = o.deletions;
                        if (u !== null) {
                            for (var c = 0; c < u.length; c++) {
                                var f = u[c];
                                for (N = f; N !== null; ) {
                                    var v = N;
                                    switch (v.tag) {
                                    case 0:
                                    case 11:
                                    case 15:
                                        mr(8, v, o)
                                    }
                                    var g = v.child;
                                    if (g !== null)
                                        g.return = v,
                                        N = g;
                                    else
                                        for (; N !== null; ) {
                                            v = N;
                                            var y = v.sibling
                                              , C = v.return;
                                            if (kd(v),
                                            v === f) {
                                                N = null;
                                                break
                                            }
                                            if (y !== null) {
                                                y.return = C,
                                                N = y;
                                                break
                                            }
                                            N = C
                                        }
                                }
                            }
                            var j = o.alternate;
                            if (j !== null) {
                                var _ = j.child;
                                if (_ !== null) {
                                    j.child = null;
                                    do {
                                        var Z = _.sibling;
                                        _.sibling = null,
                                        _ = Z
                                    } while (_ !== null)
                                }
                            }
                            N = o
                        }
                    }
                    if (o.subtreeFlags & 2064 && i !== null)
                        i.return = o,
                        N = i;
                    else
                        e: for (; N !== null; ) {
                            if (o = N,
                            o.flags & 2048)
                                switch (o.tag) {
                                case 0:
                                case 11:
                                case 15:
                                    mr(9, o, o.return)
                                }
                            var p = o.sibling;
                            if (p !== null) {
                                p.return = o.return,
                                N = p;
                                break e
                            }
                            N = o.return
                        }
                }
                var d = e.current;
                for (N = d; N !== null; ) {
                    i = N;
                    var m = i.child;
                    if (i.subtreeFlags & 2064 && m !== null)
                        m.return = i,
                        N = m;
                    else
                        e: for (i = d; N !== null; ) {
                            if (u = N,
                            u.flags & 2048)
                                try {
                                    switch (u.tag) {
                                    case 0:
                                    case 11:
                                    case 15:
                                        so(9, u)
                                    }
                                } catch (E) {
                                    ue(u, u.return, E)
                                }
                            if (u === i) {
                                N = null;
                                break e
                            }
                            var S = u.sibling;
                            if (S !== null) {
                                S.return = u.return,
                                N = S;
                                break e
                            }
                            N = u.return
                        }
                }
                if (Y = l,
                Qt(),
                at && typeof at.onPostCommitFiberRoot == "function")
                    try {
                        at.onPostCommitFiberRoot(bl, e)
                    } catch {}
                r = !0
            }
            return r
        } finally {
            G = n,
            Ye.transition = t
        }
    }
    return !1
}
function Sa(e, t, n) {
    t = Hn(n, t),
    t = cd(e, t, 1),
    e = Mt(e, t, 1),
    t = _e(),
    e !== null && (Or(e, 1, t),
    Oe(e, t))
}
function ue(e, t, n) {
    if (e.tag === 3)
        Sa(e, e, n);
    else
        for (; t !== null; ) {
            if (t.tag === 3) {
                Sa(t, e, n);
                break
            } else if (t.tag === 1) {
                var r = t.stateNode;
                if (typeof t.type.getDerivedStateFromError == "function" || typeof r.componentDidCatch == "function" && (At === null || !At.has(r))) {
                    e = Hn(n, e),
                    e = dd(t, e, 1),
                    t = Mt(t, e, 1),
                    e = _e(),
                    t !== null && (Or(t, 1, e),
                    Oe(t, e));
                    break
                }
            }
            t = t.return
        }
}
function Fh(e, t, n) {
    var r = e.pingCache;
    r !== null && r.delete(t),
    t = _e(),
    e.pingedLanes |= e.suspendedLanes & n,
    me === e && (ge & n) === n && (pe === 4 || pe === 3 && (ge & 130023424) === ge && 500 > ae() - Ms ? en(e, 0) : Os |= n),
    Oe(e, t)
}
function Nd(e, t) {
    t === 0 && (e.mode & 1 ? (t = nl,
    nl <<= 1,
    !(nl & 130023424) && (nl = 4194304)) : t = 1);
    var n = _e();
    e = St(e, t),
    e !== null && (Or(e, t, n),
    Oe(e, n))
}
function Ih(e) {
    var t = e.memoizedState
      , n = 0;
    t !== null && (n = t.retryLane),
    Nd(e, n)
}
function Rh(e, t) {
    var n = 0;
    switch (e.tag) {
    case 13:
        var r = e.stateNode
          , l = e.memoizedState;
        l !== null && (n = l.retryLane);
        break;
    case 19:
        r = e.stateNode;
        break;
    default:
        throw Error(w(314))
    }
    r !== null && r.delete(t),
    Nd(e, n)
}
var Fd;
Fd = function(e, t, n) {
    if (e !== null)
        if (e.memoizedProps !== t.pendingProps || Re.current)
            Ie = !0;
        else {
            if (!(e.lanes & n) && !(t.flags & 128))
                return Ie = !1,
                kh(e, t, n);
            Ie = !!(e.flags & 131072)
        }
    else
        Ie = !1,
        le && t.flags & 1048576 && Oc(t, Bl, t.index);
    switch (t.lanes = 0,
    t.tag) {
    case 2:
        var r = t.type;
        jl(e, t),
        e = t.pendingProps;
        var l = Wn(t, Ce.current);
        On(t, n),
        l = Ps(null, t, r, e, l, n);
        var o = Ns();
        return t.flags |= 1,
        typeof l == "object" && l !== null && typeof l.render == "function" && l.$$typeof === void 0 ? (t.tag = 1,
        t.memoizedState = null,
        t.updateQueue = null,
        De(r) ? (o = !0,
        Al(t)) : o = !1,
        t.memoizedState = l.state !== null && l.state !== void 0 ? l.state : null,
        Es(t),
        l.updater = io,
        t.stateNode = l,
        l._reactInternals = t,
        Mi(t, r, e, n),
        t = Bi(null, t, r, !0, o, n)) : (t.tag = 0,
        le && o && vs(t),
        ze(null, t, l, n),
        t = t.child),
        t;
    case 16:
        r = t.elementType;
        e: {
            switch (jl(e, t),
            e = t.pendingProps,
            l = r._init,
            r = l(r._payload),
            t.type = r,
            l = t.tag = Oh(r),
            e = Ze(r, e),
            l) {
            case 0:
                t = Wi(null, t, r, e, n);
                break e;
            case 1:
                t = ca(null, t, r, e, n);
                break e;
            case 11:
                t = ua(null, t, r, e, n);
                break e;
            case 14:
                t = aa(null, t, r, Ze(r.type, e), n);
                break e
            }
            throw Error(w(306, r, ""))
        }
        return t;
    case 0:
        return r = t.type,
        l = t.pendingProps,
        l = t.elementType === r ? l : Ze(r, l),
        Wi(e, t, r, l, n);
    case 1:
        return r = t.type,
        l = t.pendingProps,
        l = t.elementType === r ? l : Ze(r, l),
        ca(e, t, r, l, n);
    case 3:
        e: {
            if (md(t),
            e === null)
                throw Error(w(387));
            r = t.pendingProps,
            o = t.memoizedState,
            l = o.element,
            Uc(e, t),
            Hl(t, r, null, n);
            var i = t.memoizedState;
            if (r = i.element,
            o.isDehydrated)
                if (o = {
                    element: r,
                    isDehydrated: !1,
                    cache: i.cache,
                    pendingSuspenseBoundaries: i.pendingSuspenseBoundaries,
                    transitions: i.transitions
                },
                t.updateQueue.baseState = o,
                t.memoizedState = o,
                t.flags & 256) {
                    l = Hn(Error(w(423)), t),
                    t = da(e, t, r, n, l);
                    break e
                } else if (r !== l) {
                    l = Hn(Error(w(424)), t),
                    t = da(e, t, r, n, l);
                    break e
                } else
                    for (Ae = Ot(t.stateNode.containerInfo.firstChild),
                    We = t,
                    le = !0,
                    be = null,
                    n = Bc(t, null, r, n),
                    t.child = n; n; )
                        n.flags = n.flags & -3 | 4096,
                        n = n.sibling;
            else {
                if (Bn(),
                r === l) {
                    t = kt(e, t, n);
                    break e
                }
                ze(e, t, r, n)
            }
            t = t.child
        }
        return t;
    case 5:
        return Hc(t),
        e === null && Ri(t),
        r = t.type,
        l = t.pendingProps,
        o = e !== null ? e.memoizedProps : null,
        i = l.children,
        Ti(r, l) ? i = null : o !== null && Ti(r, o) && (t.flags |= 32),
        hd(e, t),
        ze(e, t, i, n),
        t.child;
    case 6:
        return e === null && Ri(t),
        null;
    case 13:
        return yd(e, t, n);
    case 4:
        return zs(t, t.stateNode.containerInfo),
        r = t.pendingProps,
        e === null ? t.child = $n(t, null, r, n) : ze(e, t, r, n),
        t.child;
    case 11:
        return r = t.type,
        l = t.pendingProps,
        l = t.elementType === r ? l : Ze(r, l),
        ua(e, t, r, l, n);
    case 7:
        return ze(e, t, t.pendingProps, n),
        t.child;
    case 8:
        return ze(e, t, t.pendingProps.children, n),
        t.child;
    case 12:
        return ze(e, t, t.pendingProps.children, n),
        t.child;
    case 10:
        e: {
            if (r = t.type._context,
            l = t.pendingProps,
            o = t.memoizedProps,
            i = l.value,
            q($l, r._currentValue),
            r._currentValue = i,
            o !== null)
                if (nt(o.value, i)) {
                    if (o.children === l.children && !Re.current) {
                        t = kt(e, t, n);
                        break e
                    }
                } else
                    for (o = t.child,
                    o !== null && (o.return = t); o !== null; ) {
                        var u = o.dependencies;
                        if (u !== null) {
                            i = o.child;
                            for (var c = u.firstContext; c !== null; ) {
                                if (c.context === r) {
                                    if (o.tag === 1) {
                                        c = gt(-1, n & -n),
                                        c.tag = 2;
                                        var f = o.updateQueue;
                                        if (f !== null) {
                                            f = f.shared;
                                            var v = f.pending;
                                            v === null ? c.next = c : (c.next = v.next,
                                            v.next = c),
                                            f.pending = c
                                        }
                                    }
                                    o.lanes |= n,
                                    c = o.alternate,
                                    c !== null && (c.lanes |= n),
                                    Di(o.return, n, t),
                                    u.lanes |= n;
                                    break
                                }
                                c = c.next
                            }
                        } else if (o.tag === 10)
                            i = o.type === t.type ? null : o.child;
                        else if (o.tag === 18) {
                            if (i = o.return,
                            i === null)
                                throw Error(w(341));
                            i.lanes |= n,
                            u = i.alternate,
                            u !== null && (u.lanes |= n),
                            Di(i, n, t),
                            i = o.sibling
                        } else
                            i = o.child;
                        if (i !== null)
                            i.return = o;
                        else
                            for (i = o; i !== null; ) {
                                if (i === t) {
                                    i = null;
                                    break
                                }
                                if (o = i.sibling,
                                o !== null) {
                                    o.return = i.return,
                                    i = o;
                                    break
                                }
                                i = i.return
                            }
                        o = i
                    }
            ze(e, t, l.children, n),
            t = t.child
        }
        return t;
    case 9:
        return l = t.type,
        r = t.pendingProps.children,
        On(t, n),
        l = Xe(l),
        r = r(l),
        t.flags |= 1,
        ze(e, t, r, n),
        t.child;
    case 14:
        return r = t.type,
        l = Ze(r, t.pendingProps),
        l = Ze(r.type, l),
        aa(e, t, r, l, n);
    case 15:
        return fd(e, t, t.type, t.pendingProps, n);
    case 17:
        return r = t.type,
        l = t.pendingProps,
        l = t.elementType === r ? l : Ze(r, l),
        jl(e, t),
        t.tag = 1,
        De(r) ? (e = !0,
        Al(t)) : e = !1,
        On(t, n),
        ad(t, r, l),
        Mi(t, r, l, n),
        Bi(null, t, r, !0, e, n);
    case 19:
        return gd(e, t, n);
    case 22:
        return pd(e, t, n)
    }
    throw Error(w(156, t.tag))
}
;
function Id(e, t) {
    return ic(e, t)
}
function Dh(e, t, n, r) {
    this.tag = e,
    this.key = n,
    this.sibling = this.child = this.return = this.stateNode = this.type = this.elementType = null,
    this.index = 0,
    this.ref = null,
    this.pendingProps = t,
    this.dependencies = this.memoizedState = this.updateQueue = this.memoizedProps = null,
    this.mode = r,
    this.subtreeFlags = this.flags = 0,
    this.deletions = null,
    this.childLanes = this.lanes = 0,
    this.alternate = null
}
function Ke(e, t, n, r) {
    return new Dh(e,t,n,r)
}
function $s(e) {
    return e = e.prototype,
    !(!e || !e.isReactComponent)
}
function Oh(e) {
    if (typeof e == "function")
        return $s(e) ? 1 : 0;
    if (e != null) {
        if (e = e.$$typeof,
        e === is)
            return 11;
        if (e === ss)
            return 14
    }
    return 2
}
function Bt(e, t) {
    var n = e.alternate;
    return n === null ? (n = Ke(e.tag, t, e.key, e.mode),
    n.elementType = e.elementType,
    n.type = e.type,
    n.stateNode = e.stateNode,
    n.alternate = e,
    e.alternate = n) : (n.pendingProps = t,
    n.type = e.type,
    n.flags = 0,
    n.subtreeFlags = 0,
    n.deletions = null),
    n.flags = e.flags & 14680064,
    n.childLanes = e.childLanes,
    n.lanes = e.lanes,
    n.child = e.child,
    n.memoizedProps = e.memoizedProps,
    n.memoizedState = e.memoizedState,
    n.updateQueue = e.updateQueue,
    t = e.dependencies,
    n.dependencies = t === null ? null : {
        lanes: t.lanes,
        firstContext: t.firstContext
    },
    n.sibling = e.sibling,
    n.index = e.index,
    n.ref = e.ref,
    n
}
function _l(e, t, n, r, l, o) {
    var i = 2;
    if (r = e,
    typeof e == "function")
        $s(e) && (i = 1);
    else if (typeof e == "string")
        i = 5;
    else
        e: switch (e) {
        case kn:
            return tn(n.children, l, o, t);
        case os:
            i = 8,
            l |= 8;
            break;
        case si:
            return e = Ke(12, n, t, l | 2),
            e.elementType = si,
            e.lanes = o,
            e;
        case ui:
            return e = Ke(13, n, t, l),
            e.elementType = ui,
            e.lanes = o,
            e;
        case ai:
            return e = Ke(19, n, t, l),
            e.elementType = ai,
            e.lanes = o,
            e;
        case Ha:
            return ao(n, l, o, t);
        default:
            if (typeof e == "object" && e !== null)
                switch (e.$$typeof) {
                case $a:
                    i = 10;
                    break e;
                case Ua:
                    i = 9;
                    break e;
                case is:
                    i = 11;
                    break e;
                case ss:
                    i = 14;
                    break e;
                case _t:
                    i = 16,
                    r = null;
                    break e
                }
            throw Error(w(130, e == null ? e : typeof e, ""))
        }
    return t = Ke(i, n, t, l),
    t.elementType = e,
    t.type = r,
    t.lanes = o,
    t
}
function tn(e, t, n, r) {
    return e = Ke(7, e, r, t),
    e.lanes = n,
    e
}
function ao(e, t, n, r) {
    return e = Ke(22, e, r, t),
    e.elementType = Ha,
    e.lanes = n,
    e.stateNode = {
        isHidden: !1
    },
    e
}
function qo(e, t, n) {
    return e = Ke(6, e, null, t),
    e.lanes = n,
    e
}
function bo(e, t, n) {
    return t = Ke(4, e.children !== null ? e.children : [], e.key, t),
    t.lanes = n,
    t.stateNode = {
        containerInfo: e.containerInfo,
        pendingChildren: null,
        implementation: e.implementation
    },
    t
}
function Mh(e, t, n, r, l) {
    this.tag = t,
    this.containerInfo = e,
    this.finishedWork = this.pingCache = this.current = this.pendingChildren = null,
    this.timeoutHandle = -1,
    this.callbackNode = this.pendingContext = this.context = null,
    this.callbackPriority = 0,
    this.eventTimes = Io(0),
    this.expirationTimes = Io(-1),
    this.entangledLanes = this.finishedLanes = this.mutableReadLanes = this.expiredLanes = this.pingedLanes = this.suspendedLanes = this.pendingLanes = 0,
    this.entanglements = Io(0),
    this.identifierPrefix = r,
    this.onRecoverableError = l,
    this.mutableSourceEagerHydrationData = null
}
function Us(e, t, n, r, l, o, i, u, c) {
    return e = new Mh(e,t,n,u,c),
    t === 1 ? (t = 1,
    o === !0 && (t |= 8)) : t = 0,
    o = Ke(3, null, null, t),
    e.current = o,
    o.stateNode = e,
    o.memoizedState = {
        element: r,
        isDehydrated: n,
        cache: null,
        transitions: null,
        pendingSuspenseBoundaries: null
    },
    Es(o),
    e
}
function Ah(e, t, n) {
    var r = 3 < arguments.length && arguments[3] !== void 0 ? arguments[3] : null;
    return {
        $$typeof: Sn,
        key: r == null ? null : "" + r,
        children: e,
        containerInfo: t,
        implementation: n
    }
}
function Rd(e) {
    if (!e)
        return Ut;
    e = e._reactInternals;
    e: {
        if (cn(e) !== e || e.tag !== 1)
            throw Error(w(170));
        var t = e;
        do {
            switch (t.tag) {
            case 3:
                t = t.stateNode.context;
                break e;
            case 1:
                if (De(t.type)) {
                    t = t.stateNode.__reactInternalMemoizedMergedChildContext;
                    break e
                }
            }
            t = t.return
        } while (t !== null);
        throw Error(w(171))
    }
    if (e.tag === 1) {
        var n = e.type;
        if (De(n))
            return Rc(e, n, t)
    }
    return t
}
function Dd(e, t, n, r, l, o, i, u, c) {
    return e = Us(n, r, !0, e, l, o, i, u, c),
    e.context = Rd(null),
    n = e.current,
    r = _e(),
    l = Wt(n),
    o = gt(r, l),
    o.callback = t ?? null,
    Mt(n, o, l),
    e.current.lanes = l,
    Or(e, l, r),
    Oe(e, r),
    e
}
function co(e, t, n, r) {
    var l = t.current
      , o = _e()
      , i = Wt(l);
    return n = Rd(n),
    t.context === null ? t.context = n : t.pendingContext = n,
    t = gt(o, i),
    t.payload = {
        element: e
    },
    r = r === void 0 ? null : r,
    r !== null && (t.callback = r),
    e = Mt(l, t, i),
    e !== null && (tt(e, l, i, o),
    kl(e, l, i)),
    i
}
function Zl(e) {
    if (e = e.current,
    !e.child)
        return null;
    switch (e.child.tag) {
    case 5:
        return e.child.stateNode;
    default:
        return e.child.stateNode
    }
}
function ka(e, t) {
    if (e = e.memoizedState,
    e !== null && e.dehydrated !== null) {
        var n = e.retryLane;
        e.retryLane = n !== 0 && n < t ? n : t
    }
}
function Hs(e, t) {
    ka(e, t),
    (e = e.alternate) && ka(e, t)
}
function Wh() {
    return null
}
var Od = typeof reportError == "function" ? reportError : function(e) {
    console.error(e)
}
;
function Vs(e) {
    this._internalRoot = e
}
fo.prototype.render = Vs.prototype.render = function(e) {
    var t = this._internalRoot;
    if (t === null)
        throw Error(w(409));
    co(e, t, null, null)
}
;
fo.prototype.unmount = Vs.prototype.unmount = function() {
    var e = this._internalRoot;
    if (e !== null) {
        this._internalRoot = null;
        var t = e.containerInfo;
        un(function() {
            co(null, e, null, null)
        }),
        t[xt] = null
    }
}
;
function fo(e) {
    this._internalRoot = e
}
fo.prototype.unstable_scheduleHydration = function(e) {
    if (e) {
        var t = pc();
        e = {
            blockedOn: null,
            target: e,
            priority: t
        };
        for (var n = 0; n < Tt.length && t !== 0 && t < Tt[n].priority; n++)
            ;
        Tt.splice(n, 0, e),
        n === 0 && mc(e)
    }
}
;
function Qs(e) {
    return !(!e || e.nodeType !== 1 && e.nodeType !== 9 && e.nodeType !== 11)
}
function po(e) {
    return !(!e || e.nodeType !== 1 && e.nodeType !== 9 && e.nodeType !== 11 && (e.nodeType !== 8 || e.nodeValue !== " react-mount-point-unstable "))
}
function wa() {}
function Bh(e, t, n, r, l) {
    if (l) {
        if (typeof r == "function") {
            var o = r;
            r = function() {
                var f = Zl(i);
                o.call(f)
            }
        }
        var i = Dd(t, r, e, 0, null, !1, !1, "", wa);
        return e._reactRootContainer = i,
        e[xt] = i.current,
        zr(e.nodeType === 8 ? e.parentNode : e),
        un(),
        i
    }
    for (; l = e.lastChild; )
        e.removeChild(l);
    if (typeof r == "function") {
        var u = r;
        r = function() {
            var f = Zl(c);
            u.call(f)
        }
    }
    var c = Us(e, 0, !1, null, null, !1, !1, "", wa);
    return e._reactRootContainer = c,
    e[xt] = c.current,
    zr(e.nodeType === 8 ? e.parentNode : e),
    un(function() {
        co(t, c, n, r)
    }),
    c
}
function ho(e, t, n, r, l) {
    var o = n._reactRootContainer;
    if (o) {
        var i = o;
        if (typeof l == "function") {
            var u = l;
            l = function() {
                var c = Zl(i);
                u.call(c)
            }
        }
        co(t, i, e, l)
    } else
        i = Bh(n, t, e, l, r);
    return Zl(i)
}
dc = function(e) {
    switch (e.tag) {
    case 3:
        var t = e.stateNode;
        if (t.current.memoizedState.isDehydrated) {
            var n = sr(t.pendingLanes);
            n !== 0 && (cs(t, n | 1),
            Oe(t, ae()),
            !(Y & 6) && (Vn = ae() + 500,
            Qt()))
        }
        break;
    case 13:
        un(function() {
            var r = St(e, 1);
            if (r !== null) {
                var l = _e();
                tt(r, e, 1, l)
            }
        }),
        Hs(e, 1)
    }
}
;
ds = function(e) {
    if (e.tag === 13) {
        var t = St(e, 134217728);
        if (t !== null) {
            var n = _e();
            tt(t, e, 134217728, n)
        }
        Hs(e, 134217728)
    }
}
;
fc = function(e) {
    if (e.tag === 13) {
        var t = Wt(e)
          , n = St(e, t);
        if (n !== null) {
            var r = _e();
            tt(n, e, t, r)
        }
        Hs(e, t)
    }
}
;
pc = function() {
    return G
}
;
hc = function(e, t) {
    var n = G;
    try {
        return G = e,
        t()
    } finally {
        G = n
    }
}
;
xi = function(e, t, n) {
    switch (t) {
    case "input":
        if (fi(e, n),
        t = n.name,
        n.type === "radio" && t != null) {
            for (n = e; n.parentNode; )
                n = n.parentNode;
            for (n = n.querySelectorAll("input[name=" + JSON.stringify("" + t) + '][type="radio"]'),
            t = 0; t < n.length; t++) {
                var r = n[t];
                if (r !== e && r.form === e.form) {
                    var l = ro(r);
                    if (!l)
                        throw Error(w(90));
                    Qa(r),
                    fi(r, l)
                }
            }
        }
        break;
    case "textarea":
        Ya(e, n);
        break;
    case "select":
        t = n.value,
        t != null && Fn(e, !!n.multiple, t, !1)
    }
}
;
ec = As;
tc = un;
var $h = {
    usingClientEntryPoint: !1,
    Events: [Ar, En, ro, qa, ba, As]
}
  , rr = {
    findFiberByHostInstance: Zt,
    bundleType: 0,
    version: "18.3.1",
    rendererPackageName: "react-dom"
}
  , Uh = {
    bundleType: rr.bundleType,
    version: rr.version,
    rendererPackageName: rr.rendererPackageName,
    rendererConfig: rr.rendererConfig,
    overrideHookState: null,
    overrideHookStateDeletePath: null,
    overrideHookStateRenamePath: null,
    overrideProps: null,
    overridePropsDeletePath: null,
    overridePropsRenamePath: null,
    setErrorHandler: null,
    setSuspenseHandler: null,
    scheduleUpdate: null,
    currentDispatcherRef: wt.ReactCurrentDispatcher,
    findHostInstanceByFiber: function(e) {
        return e = lc(e),
        e === null ? null : e.stateNode
    },
    findFiberByHostInstance: rr.findFiberByHostInstance || Wh,
    findHostInstancesForRefresh: null,
    scheduleRefresh: null,
    scheduleRoot: null,
    setRefreshHandler: null,
    getCurrentFiber: null,
    reconcilerVersion: "18.3.1-next-f1338f8080-20240426"
};
if (typeof __REACT_DEVTOOLS_GLOBAL_HOOK__ < "u") {
    var pl = __REACT_DEVTOOLS_GLOBAL_HOOK__;
    if (!pl.isDisabled && pl.supportsFiber)
        try {
            bl = pl.inject(Uh),
            at = pl
        } catch {}
}
$e.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED = $h;
$e.createPortal = function(e, t) {
    var n = 2 < arguments.length && arguments[2] !== void 0 ? arguments[2] : null;
    if (!Qs(t))
        throw Error(w(200));
    return Ah(e, t, null, n)
}
;
$e.createRoot = function(e, t) {
    if (!Qs(e))
        throw Error(w(299));
    var n = !1
      , r = ""
      , l = Od;
    return t != null && (t.unstable_strictMode === !0 && (n = !0),
    t.identifierPrefix !== void 0 && (r = t.identifierPrefix),
    t.onRecoverableError !== void 0 && (l = t.onRecoverableError)),
    t = Us(e, 1, !1, null, null, n, !1, r, l),
    e[xt] = t.current,
    zr(e.nodeType === 8 ? e.parentNode : e),
    new Vs(t)
}
;
$e.findDOMNode = function(e) {
    if (e == null)
        return null;
    if (e.nodeType === 1)
        return e;
    var t = e._reactInternals;
    if (t === void 0)
        throw typeof e.render == "function" ? Error(w(188)) : (e = Object.keys(e).join(","),
        Error(w(268, e)));
    return e = lc(t),
    e = e === null ? null : e.stateNode,
    e
}
;
$e.flushSync = function(e) {
    return un(e)
}
;
$e.hydrate = function(e, t, n) {
    if (!po(t))
        throw Error(w(200));
    return ho(null, e, t, !0, n)
}
;
$e.hydrateRoot = function(e, t, n) {
    if (!Qs(e))
        throw Error(w(405));
    var r = n != null && n.hydratedSources || null
      , l = !1
      , o = ""
      , i = Od;
    if (n != null && (n.unstable_strictMode === !0 && (l = !0),
    n.identifierPrefix !== void 0 && (o = n.identifierPrefix),
    n.onRecoverableError !== void 0 && (i = n.onRecoverableError)),
    t = Dd(t, null, e, 1, n ?? null, l, !1, o, i),
    e[xt] = t.current,
    zr(e),
    r)
        for (e = 0; e < r.length; e++)
            n = r[e],
            l = n._getVersion,
            l = l(n._source),
            t.mutableSourceEagerHydrationData == null ? t.mutableSourceEagerHydrationData = [n, l] : t.mutableSourceEagerHydrationData.push(n, l);
    return new fo(t)
}
;
$e.render = function(e, t, n) {
    if (!po(t))
        throw Error(w(200));
    return ho(null, e, t, !1, n)
}
;
$e.unmountComponentAtNode = function(e) {
    if (!po(e))
        throw Error(w(40));
    return e._reactRootContainer ? (un(function() {
        ho(null, null, e, !1, function() {
            e._reactRootContainer = null,
            e[xt] = null
        })
    }),
    !0) : !1
}
;
$e.unstable_batchedUpdates = As;
$e.unstable_renderSubtreeIntoContainer = function(e, t, n, r) {
    if (!po(n))
        throw Error(w(200));
    if (e == null || e._reactInternals === void 0)
        throw Error(w(38));
    return ho(e, t, n, !1, r)
}
;
$e.version = "18.3.1-next-f1338f8080-20240426";
function Md() {
    if (!(typeof __REACT_DEVTOOLS_GLOBAL_HOOK__ > "u" || typeof __REACT_DEVTOOLS_GLOBAL_HOOK__.checkDCE != "function"))
        try {
            __REACT_DEVTOOLS_GLOBAL_HOOK__.checkDCE(Md)
        } catch (e) {
            console.error(e)
        }
}
Md(),
Ma.exports = $e;
var Hh = Ma.exports
  , Ca = Hh;
oi.createRoot = Ca.createRoot,
oi.hydrateRoot = Ca.hydrateRoot;
const O = "#35644F"
  , Fe = "#F7F6F3"
  , Q = "#2A2A2A"
  , M = "#6B6B6B"
  , V = "#E0DDD6"
  , nn = "#C53030"
  , X = "#FFFFFF"
  , ja = ["Produce", "Dairy & Eggs", "Meat & Seafood", "Bakery", "Frozen", "Pantry", "Beverages", "Household", "Other"]
  , k = "'Avenir', 'Avenir Next', -apple-system, 'Segoe UI', sans-serif";
function lr(e) {
    return e.length === 0 ? "" : e.length <= 3 ? `(${e}` : e.length <= 6 ? `(${e.slice(0, 3)}) ${e.slice(3)}` : `(${e.slice(0, 3)}) ${e.slice(3, 6)}-${e.slice(6, 10)}`
}
function ei() {
    return s.jsxs("svg", {
        width: "72",
        height: "72",
        viewBox: "0 0 72 72",
        fill: "none",
        xmlns: "http://www.w3.org/2000/svg",
        "aria-label": "Thriftly logo",
        children: [s.jsx("rect", {
            x: "12",
            y: "10",
            width: "42",
            height: "52",
            rx: "6",
            stroke: O,
            strokeWidth: "2.5",
            fill: X
        }), s.jsx("rect", {
            x: "25",
            y: "4",
            width: "16",
            height: "10",
            rx: "4",
            fill: O
        }), s.jsx("rect", {
            x: "29",
            y: "7",
            width: "8",
            height: "4",
            rx: "2",
            fill: X
        }), s.jsx("path", {
            d: "M20 27 L23 30 L28 24",
            stroke: O,
            strokeWidth: "2.2",
            strokeLinecap: "round",
            strokeLinejoin: "round"
        }), s.jsx("line", {
            x1: "33",
            y1: "27",
            x2: "46",
            y2: "27",
            stroke: O,
            strokeWidth: "2",
            strokeLinecap: "round",
            opacity: "0.7"
        }), s.jsx("path", {
            d: "M20 37 L23 40 L28 34",
            stroke: O,
            strokeWidth: "2.2",
            strokeLinecap: "round",
            strokeLinejoin: "round"
        }), s.jsx("line", {
            x1: "33",
            y1: "37",
            x2: "42",
            y2: "37",
            stroke: O,
            strokeWidth: "2",
            strokeLinecap: "round",
            opacity: "0.7"
        }), s.jsx("circle", {
            cx: "24",
            cy: "47",
            r: "2",
            fill: O,
            opacity: "0.3"
        }), s.jsx("line", {
            x1: "33",
            y1: "47",
            x2: "39",
            y2: "47",
            stroke: O,
            strokeWidth: "2",
            strokeLinecap: "round",
            opacity: "0.3"
        }), s.jsx("path", {
            d: "M54 14 L56 19 L61 21 L56 23 L54 28 L52 23 L47 21 L52 19 Z",
            fill: O,
            children: s.jsx("animateTransform", {
                attributeName: "transform",
                type: "rotate",
                from: "0 54 21",
                to: "360 54 21",
                dur: "12s",
                repeatCount: "indefinite"
            })
        }), s.jsx("path", {
            d: "M60 6 L61 9 L64 10 L61 11 L60 14 L59 11 L56 10 L59 9 Z",
            fill: O,
            opacity: "0.5"
        })]
    })
}
function ti({size: e=28}) {
    return s.jsx("div", {
        style: {
            width: e,
            height: e,
            borderRadius: "50%",
            overflow: "hidden",
            flexShrink: 0,
            backgroundColor: "#e8e4df",
            border: e > 40 ? `2px solid ${V}` : "none"
        },
        children: s.jsx("img", {
            src: "/penny.png",
            alt: "Penny",
            width: e,
            height: e,
            style: {
                objectFit: "cover",
                objectPosition: "center 15%",
                display: "block"
            }
        })
    })
}
const Vh = ["Reading your list...", "Let me see what you wrote...", "Hmm, looking at this..."]
  , Qh = ["Checking it twice!", "Sorting by aisle...", "Ooh, good choices!", "I know just where these go..."]
  , Kh = ["Adding to your list...", "Almost done!", "Stocking up!"]
  , ni = [Vh, Qh, Kh];
function ri(e) {
    return e[Math.floor(Math.random() * e.length)]
}
function hl({isOpen: e, onClose: t, title: n, children: r, maxHeight: l}) {
    return e ? s.jsx("div", {
        style: z.overlay,
        onClick: t,
        children: s.jsxs("div", {
            style: {
                ...z.sheet,
                ...l ? {
                    maxHeight: l
                } : {}
            },
            onClick: o => o.stopPropagation(),
            children: [n && s.jsx("p", {
                style: z.sheetTitle,
                children: n
            }), r]
        })
    }) : null
}
function ml({label: e}) {
    return s.jsx("p", {
        style: {
            fontFamily: k,
            fontSize: "13px",
            fontWeight: 600,
            color: M,
            textTransform: "uppercase",
            letterSpacing: "0.5px",
            marginBottom: "12px"
        },
        children: e
    })
}
function Yh({value: e, onChange: t}) {
    return s.jsxs("div", {
        style: {
            display: "flex",
            alignItems: "center",
            gap: "0",
            border: `1.5px solid ${V}`,
            borderRadius: "10px",
            overflow: "hidden",
            backgroundColor: Fe,
            flexShrink: 0
        },
        children: [s.jsx("button", {
            onClick: () => t(Math.max(1, e - 1)),
            style: {
                width: "34px",
                height: "34px",
                border: "none",
                background: "none",
                fontSize: "18px",
                color: O,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center"
            },
            children: "−"
        }), s.jsx("span", {
            style: {
                fontFamily: k,
                fontSize: "15px",
                fontWeight: 600,
                color: Q,
                minWidth: "24px",
                textAlign: "center"
            },
            children: e
        }), s.jsx("button", {
            onClick: () => t(e + 1),
            style: {
                width: "34px",
                height: "34px",
                border: "none",
                background: "none",
                fontSize: "18px",
                color: O,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center"
            },
            children: "+"
        })]
    })
}
function li({open: e, title: t, message: n, confirmLabel: r, onConfirm: l, onCancel: o, destructive: i}) {
    return e ? s.jsx("div", {
        onClick: o,
        style: {
            position: "fixed",
            inset: 0,
            zIndex: 9999,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            backgroundColor: "rgba(0,0,0,0.4)"
        },
        children: s.jsxs("div", {
            onClick: u => u.stopPropagation(),
            style: {
                backgroundColor: "#fff",
                borderRadius: "14px",
                width: "270px",
                overflow: "hidden",
                textAlign: "center",
                fontFamily: k
            },
            children: [s.jsxs("div", {
                style: {
                    padding: "20px 16px 0"
                },
                children: [s.jsx("div", {
                    style: {
                        fontSize: "17px",
                        fontWeight: 600,
                        color: Q
                    },
                    children: t
                }), n && s.jsx("div", {
                    style: {
                        fontSize: "13px",
                        color: M,
                        marginTop: "4px"
                    },
                    children: n
                })]
            }), s.jsxs("div", {
                style: {
                    display: "flex",
                    borderTop: "1px solid #e5e5e5",
                    marginTop: "16px"
                },
                children: [s.jsx("button", {
                    onClick: o,
                    style: {
                        flex: 1,
                        padding: "12px",
                        border: "none",
                        background: "none",
                        fontSize: "17px",
                        fontFamily: k,
                        color: "#007AFF",
                        cursor: "pointer",
                        borderRight: "1px solid #e5e5e5"
                    },
                    children: "Cancel"
                }), s.jsx("button", {
                    onClick: l,
                    style: {
                        flex: 1,
                        padding: "12px",
                        border: "none",
                        background: "none",
                        fontSize: "17px",
                        fontWeight: 600,
                        fontFamily: k,
                        cursor: "pointer",
                        color: i ? nn : "#007AFF"
                    },
                    children: r || "Confirm"
                })]
            })]
        })
    }) : null
}
function Ea() {
    return s.jsxs(s.Fragment, {
        children: [s.jsxs("a", {
            href: "https://thrift.ly",
            target: "_blank",
            rel: "noopener noreferrer",
            style: {
                fontFamily: k,
                fontSize: "12px",
                color: M,
                textDecoration: "none",
                marginTop: "48px",
                opacity: .5
            },
            children: ["powered by ", s.jsx("span", {
                style: {
                    fontWeight: 600
                },
                children: "thriftly"
            })]
        }), s.jsxs("div", {
            style: {
                fontFamily: k,
                fontSize: "11px",
                color: M,
                marginTop: "12px",
                opacity: .45
            },
            children: [s.jsx("a", {
                href: "/privacy",
                target: "_blank",
                rel: "noopener noreferrer",
                style: {
                    color: M,
                    textDecoration: "none"
                },
                children: "Privacy"
            }), " · ", s.jsx("a", {
                href: "/terms",
                target: "_blank",
                rel: "noopener noreferrer",
                style: {
                    color: M,
                    textDecoration: "none"
                },
                children: "Terms"
            })]
        })]
    })
}
function Xh() {
    const [e,t] = T.useState("phone")
      , n = a => {
        t(a),
        ["home", "settings", "about", "invite", "saved", "settings-profile", "settings-family", "settings-share", "admin"].includes(a) && (window.location.hash = a === "home" ? "" : a),
        typeof gtag == "function" && gtag("event", "page_view", {
            page_title: a
        })
    }
      , [r,l] = T.useState("")
      , [o,i] = T.useState(["", "", "", "", "", ""])
      , [u,c] = T.useState("")
      , [f,v] = T.useState(!1)
      , [g,y] = T.useState(!0)
      , [C,j] = T.useState([])
      , [_,Z] = T.useState("")
      , [p,d] = T.useState(!1)
      , [m,S] = T.useState(null)
      , [E,I] = T.useState(null)
      , [F,R] = T.useState("")
      , [te,$] = T.useState("")
      , [Pe,Ct] = T.useState("")
      , [jt,Xn] = T.useState(1)
      , [Br,dn] = T.useState("")
      , [rt,L] = T.useState(!1)
      , [A,W] = T.useState([])
      , ne = T.useRef({})
      , [U,dt] = T.useState(null)
      , je = T.useRef(null)
      , [Ee,xe] = T.useState([])
      , [He,Gn] = T.useState([])
      , [Wd,fn] = T.useState(!1)
      , [pn,mo] = T.useState(null)
      , Ks = T.useRef(null)
      , [Ys,lt] = T.useState(!1)
      , [Bd,hn] = T.useState(!1)
      , [Xs,$d] = T.useState([])
      , [Ud,$r] = T.useState(!1)
      , [mn,Ur] = T.useState("")
      , [Et,Hr] = T.useState(null)
      , [B,Gs] = T.useState(null)
      , yo = T.useRef(null)
      , go = a => {
        yo.current = a.onConfirm,
        Gs({
            title: a.title,
            message: a.message,
            confirmLabel: a.confirmLabel,
            destructive: a.destructive
        })
    }
      , Vr = () => {
        Gs(null),
        yo.current = null
    }
      , vo = () => {
        const a = yo.current;
        Vr(),
        a && a()
    }
      , [Js,Zs] = T.useState("")
      , [xo,qs] = T.useState("")
      , [bs,Hd] = T.useState([])
      , [Qr,eu] = T.useState(!1)
      , [Kr,tu] = T.useState(!1)
      , [Vd,Qd] = T.useState("")
      , [yn,Kd] = T.useState([])
      , [Yd,nu] = T.useState(!1)
      , [Kt,Xd] = T.useState(null)
      , [Yr,Gd] = T.useState(30)
      , [Xr,Jd] = T.useState(!0)
      , [gn,So] = T.useState(null)
      , [Gr,ko] = T.useState(null)
      , wo = T.useRef(null)
      , Co = T.useRef(-1)
      , Zd = ["Looking good!", "Almost there!", "Penny approves!", "Great picks!", "Nice work!", "On a roll!", "Crushing it!", "Keep going!"];
    T.useEffect( () => {
        const a = C.filter(h => h.checked).length;
        a > Co.current && Co.current >= 0 && C.length > 0 && Math.random() < .3 && (wo.current && clearTimeout(wo.current),
        ko(ri(Zd)),
        wo.current = setTimeout( () => ko(null), 4e3)),
        Co.current = a
    }
    , [C]),
    T.useEffect( () => {
        if (!p) {
            So(null);
            return
        }
        let a = 0;
        So(ri(ni[0]));
        const h = setInterval( () => {
            a = (a + 1) % ni.length,
            So(ri(ni[a]))
        }
        , 2e3);
        return () => clearInterval(h)
    }
    , [p]);
    const ru = T.useRef(null)
      , Yt = T.useRef([]);
    T.useEffect( () => {
        const a = window.location.pathname
          , h = a.match(/^\/join\/(.+)$/);
        h && (localStorage.setItem("thriftly_join_code", h[1]),
        window.history.replaceState({}, "", "/"));
        const x = a.match(/^\/r\/(.+)$/);
        x && (localStorage.setItem("referral_code", x[1]),
        window.history.replaceState({}, "", "/"))
    }
    , []);
    const lu = T.useCallback(async () => {
        const a = localStorage.getItem("thriftly_join_code");
        if (a)
            try {
                const x = await fetch("/api/join", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        code: a
                    })
                });
                if (x.ok)
                    localStorage.removeItem("thriftly_join_code"),
                    J("Joined family list!");
                else {
                    localStorage.removeItem("thriftly_join_code");
                    const P = await x.json().catch( () => null);
                    P != null && P.error && J(P.error, "error")
                }
            } catch {
                localStorage.removeItem("thriftly_join_code")
            }
        const h = localStorage.getItem("referral_code");
        if (h) {
            try {
                await fetch("/api/referral/claim", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        code: h
                    })
                })
            } catch {}
            localStorage.removeItem("referral_code")
        }
    }
    , []);
    T.useEffect( () => {
        fetch("/auth/me").then(a => {
            if (a.ok) {
                a.clone().json().then(P => {
                    P.is_admin && nu(!0)
                }
                ).catch( () => {}
                ),
                lu();
                const h = window.location.hash.replace("#", "");
                n(["home", "settings", "about", "invite", "saved", "settings-profile", "settings-family", "settings-share", "admin"].includes(h) ? h : "home")
            }
        }
        ).catch( () => {}
        ).finally( () => y(!1))
    }
    , []),
    T.useEffect( () => {
        e === "phone" && !g && setTimeout( () => {
            var a;
            return (a = ru.current) == null ? void 0 : a.focus()
        }
        , 150),
        e === "code" && setTimeout( () => {
            var a;
            return (a = Yt.current[0]) == null ? void 0 : a.focus()
        }
        , 150)
    }
    , [e, g]);
    const vn = a => [...a].sort( (h, x) => h.name.localeCompare(x.name))
      , jo = () => {
        n("phone"),
        l(""),
        c(""),
        J("Session expired — please log in again", "error")
    }
      , qd = async () => {
        const a = await fetch("/api/list");
        if (a.status === 401) {
            jo();
            return
        }
        if (a.ok) {
            const h = await a.json();
            j(vn(Array.isArray(h) ? h : []))
        }
    }
    ;
    T.useEffect( () => {
        e === "home" && qd().catch( () => {}
        )
    }
    , [e]);
    const ou = () => {
        fetch("/api/saved-lists").then(a => a.ok ? a.json() : []).then(a => $d(Array.isArray(a) ? [...a].sort( (h, x) => h.name.localeCompare(x.name)) : [])).catch( () => {}
        )
    }
    ;
    T.useEffect( () => {
        e === "saved" && ou()
    }
    , [e]);
    const iu = () => {
        fetch("/api/settings").then(a => a.ok ? a.json() : null).then(a => {
            a && (Zs(a.name || ""),
            qs(a.email || ""),
            Hd(a.household_members || []))
        }
        ).catch( () => {}
        )
    }
    ;
    T.useEffect( () => {
        ["settings", "about", "invite", "settings-profile", "settings-family"].includes(e) && iu()
    }
    , [e]);
    const bd = () => {
        fetch("/api/referral").then(a => a.ok ? a.json() : null).then(a => {
            a && (Qd(a.code || ""),
            Kd(a.friends || []))
        }
        ).catch( () => {}
        )
    }
    ;
    T.useEffect( () => {
        e === "settings-share" && bd()
    }
    , [e]),
    T.useEffect( () => {
        e === "admin" && fetch(`/api/admin/dashboard?days=${Yr}`).then(a => a.ok ? a.json() : null).then(a => {
            a && Xd(a)
        }
        ).catch( () => {}
        )
    }
    , [e, Yr]),
    T.useEffect( () => {
        e === "invite" && n("settings-family")
    }
    , [e]);
    const J = (a, h="success") => {
        je.current && clearTimeout(je.current),
        dt({
            message: a,
            type: h
        }),
        je.current = setTimeout( () => dt(null), 5e3)
    }
      , ef = a => {
        var P;
        const h = (P = a.target.files) == null ? void 0 : P[0];
        if (!h)
            return;
        const x = new Image;
        x.onload = () => {
            let D = x.width
              , re = x.height;
            (D > 1024 || re > 1024) && (D > re ? (re = Math.round(re * 1024 / D),
            D = 1024) : (D = Math.round(D * 1024 / re),
            re = 1024));
            const ot = document.createElement("canvas");
            ot.width = D,
            ot.height = re;
            const ft = ot.getContext("2d");
            ft == null || ft.drawImage(x, 0, 0, D, re),
            mo(ot.toDataURL("image/jpeg", .8))
        }
        ,
        x.src = URL.createObjectURL(h),
        a.target.value = ""
    }
      , su = async a => {
        j(h => {
            const x = h.map(P => P.id === a ? {
                ...P,
                checked: !P.checked
            } : P);
            return x.length > 0 && x.every(P => P.checked) && setTimeout( () => hn(!0), 300),
            x
        }
        );
        try {
            const h = await fetch(`/api/list/${a}/toggle`, {
                method: "PATCH"
            });
            if (h.ok) {
                const x = await h.json();
                j(P => {
                    const K = P.map(D => D.id === x.id ? x : D);
                    return K.length > 0 && K.every(D => D.checked) && setTimeout( () => hn(!0), 300),
                    K
                }
                )
            }
        } catch {}
    }
      , uu = async () => {
        if (!(!_.trim() && !pn || p)) {
            d(!0),
            xe([]),
            Gn([]);
            try {
                const a = JSON.stringify({
                    text: _.trim(),
                    image: pn || ""
                });
                console.log("[penny] sending parse request, payload size:", a.length);
                const h = await fetch("/api/list/parse", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: a
                });
                if (console.log("[penny] parse response status:", h.status),
                h.ok) {
                    const x = await h.json()
                      , P = x.items || []
                      , K = x.skipped || [];
                    j(re => {
                        const ot = new Map(re.map(ft => [ft.id, ft]));
                        for (const ft of P)
                            ot.set(ft.id, ft);
                        return vn(Array.from(ot.values()))
                    }
                    ),
                    xe(P),
                    Gn(K),
                    Z(""),
                    mo(null);
                    const D = [];
                    x.added > 0 && D.push(`Added ${x.added} item${x.added === 1 ? "" : "s"}!`),
                    K.length > 0 && D.push(`${K.length} already on your list`),
                    D.length > 0 ? J(D.join(" · ")) : P.length === 0 && K.length === 0 && J("No items found", "error")
                } else if (h.status === 401)
                    n("phone"),
                    l(""),
                    c(""),
                    J("Session expired — please log in again", "error");
                else {
                    const x = await h.json().catch( () => null)
                      , P = (x == null ? void 0 : x.error) || `Error ${h.status}`;
                    console.error("[penny] parse failed:", h.status, P),
                    J(P, "error")
                }
            } catch (a) {
                console.error("[penny] parse error:", a),
                J("Network error", "error")
            } finally {
                d(!1)
            }
        }
    }
      , tf = a => {
        I(a),
        R(a.name),
        $(a.brand),
        Ct(a.department),
        Xn(a.quantity || 1),
        dn(a.size),
        W([]),
        fetch(`/api/list/${a.id}/history`).then(h => h.ok ? h.json() : []).then(h => W(Array.isArray(h) ? h : [])).catch( () => {}
        )
    }
      , nf = async () => {
        if (!(!E || !F.trim() || rt)) {
            L(!0);
            try {
                const a = await fetch(`/api/list/${E.id}`, {
                    method: "PATCH",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        name: F.trim(),
                        brand: te.trim(),
                        department: Pe,
                        quantity: jt,
                        size: Br.trim()
                    })
                });
                if (a.ok) {
                    const h = await a.json();
                    j(x => vn(x.map(P => P.id === h.id ? h : P))),
                    I(null)
                }
            } catch {} finally {
                L(!1)
            }
        }
    }
      , rf = async () => {
        if (!(!E || rt)) {
            L(!0);
            try {
                (await fetch(`/api/list/${E.id}`, {
                    method: "DELETE"
                })).ok && (j(h => h.filter(x => x.id !== E.id)),
                I(null))
            } catch {} finally {
                L(!1)
            }
        }
    }
      , au = () => {
        fetch("/api/list/clear", {
            method: "POST"
        }).then(a => {
            if (a.status === 401) {
                jo();
                return
            }
            if (!a.ok) {
                J("Failed to clear list", "error");
                return
            }
            j([]),
            hn(!1),
            ko(null),
            J("List cleared")
        }
        ).catch( () => J("Failed to clear list", "error"))
    }
      , cu = async () => {
        if (mn.trim())
            try {
                const a = await fetch("/api/saved-lists", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        name: mn.trim()
                    })
                });
                if (a.ok)
                    $r(!1),
                    Ur(""),
                    J("List saved!");
                else {
                    const h = await a.json().catch( () => null);
                    J((h == null ? void 0 : h.error) || "Failed to save list", "error")
                }
            } catch {
                J("Failed to save list", "error")
            }
    }
      , du = (a, h="merge") => {
        const x = h === "overwrite" ? `/api/saved-lists/${a}/load?mode=overwrite` : `/api/saved-lists/${a}/load`;
        Hr(null),
        fetch(x, {
            method: "POST"
        }).then(P => {
            if (P.status === 401) {
                jo();
                return
            }
            if (!P.ok) {
                J("Failed to load list", "error");
                return
            }
            n("home"),
            J(h === "overwrite" ? "List replaced!" : "List merged!")
        }
        ).catch( () => J("Failed to load list", "error"))
    }
      , lf = async a => {
        try {
            (await fetch(`/api/saved-lists/${a}`, {
                method: "DELETE"
            })).ok && (Hr(null),
            ou(),
            J("List deleted"))
        } catch {
            J("Failed to delete list", "error")
        }
    }
      , of = a => {
        let h = a.target.value.replace(/\D/g, "");
        h.length > 10 && h.startsWith("1") && (h = h.slice(1)),
        l(h.slice(0, 10)),
        c("")
    }
      , fu = async () => {
        if (!(r.length !== 10 || f)) {
            v(!0),
            c("");
            try {
                const a = await fetch("/auth/send-code", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        phone_number: r
                    })
                })
                  , h = await a.json();
                a.ok ? (n("code"),
                i(["", "", "", "", "", ""])) : c(h.error || "Failed to send code")
            } catch {
                c("Network error. Please try again.")
            } finally {
                v(!1)
            }
        }
    }
      , Eo = T.useRef(!1)
      , pu = T.useCallback(async a => {
        if (!Eo.current) {
            Eo.current = !0,
            v(!0),
            c("");
            try {
                const h = await fetch("/auth/verify-code", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        phone_number: r,
                        code: a
                    })
                })
                  , x = await h.json();
                h.ok ? (x.is_admin && nu(!0),
                lu(),
                n("home")) : (c(x.error || "Invalid code"),
                i(["", "", "", "", "", ""]),
                setTimeout( () => {
                    var P;
                    return (P = Yt.current[0]) == null ? void 0 : P.focus()
                }
                , 50))
            } catch {
                c("Network error. Please try again."),
                i(["", "", "", "", "", ""])
            } finally {
                v(!1),
                Eo.current = !1
            }
        }
    }
    , [r])
      , sf = (a, h) => {
        var K;
        const x = h.replace(/\D/g, "").slice(-1)
          , P = [...o];
        P[a] = x,
        i(P),
        c(""),
        x && a < 5 && ((K = Yt.current[a + 1]) == null || K.focus()),
        x && P.join("").length === 6 && pu(P.join(""))
    }
      , uf = (a, h) => {
        var x;
        h.key === "Backspace" && !o[a] && a > 0 && ((x = Yt.current[a - 1]) == null || x.focus())
    }
      , af = a => {
        var K, D;
        a.preventDefault();
        const h = a.clipboardData.getData("text").replace(/\D/g, "").slice(0, 6);
        if (h.length === 0)
            return;
        const x = [...o];
        for (let re = 0; re < h.length && re < 6; re++)
            x[re] = h[re];
        i(x);
        const P = x.findIndex(re => !re);
        P >= 0 ? (K = Yt.current[P]) == null || K.focus() : ((D = Yt.current[5]) == null || D.focus(),
        pu(x.join("")))
    }
      , cf = async () => {
        if (!Qr) {
            eu(!0);
            try {
                const a = await fetch("/api/settings", {
                    method: "PATCH",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        name: Js.trim(),
                        email: xo.trim()
                    })
                });
                if (a.ok)
                    J("Settings saved!");
                else {
                    const h = await a.json().catch( () => null);
                    J((h == null ? void 0 : h.error) || "Failed to save", "error")
                }
            } catch {
                J("Network error", "error")
            } finally {
                eu(!1)
            }
        }
    }
      , df = async a => {
        if (!Kr) {
            tu(!0);
            try {
                const h = await fetch("/api/settings/invite", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        phone: ""
                    })
                });
                if (h.ok) {
                    const x = await h.json();
                    x.link && a(x.link)
                } else {
                    const x = await h.json().catch( () => null);
                    J((x == null ? void 0 : x.error) || "Failed to create invite", "error")
                }
            } catch {
                J("Network error", "error")
            } finally {
                tu(!1)
            }
        }
    }
      , ff = () => df(a => {
        const h = `Join our family shopping list on Thriftly! ${a}`;
        window.location.href = `sms:?&body=${encodeURIComponent(h)}`
    }
    )
      , hu = async () => {
        await fetch("/auth/logout", {
            method: "POST"
        }),
        lt(!1),
        n("phone"),
        l(""),
        i(["", "", "", "", "", ""]),
        c("")
    }
    ;
    if (g)
        return s.jsx("div", {
            style: ce.container,
            children: s.jsx("div", {
                style: ce.card,
                children: s.jsx(ei, {})
            })
        });
    if (e === "phone") {
        const a = r.length === 10;
        return s.jsx("div", {
            style: ce.container,
            children: s.jsxs("div", {
                style: ce.card,
                children: [s.jsx(ei, {}), s.jsx("h1", {
                    style: ce.wordmark,
                    children: "Shared shopping list"
                }), s.jsx("p", {
                    style: ce.tagline,
                    children: "Penny AI accepts texts, emails, and photos, and organizes a clean, simple list"
                }), s.jsxs("div", {
                    style: ce.inputGroup,
                    children: [s.jsx("label", {
                        style: ce.label,
                        children: "Phone number"
                    }), s.jsx("input", {
                        ref: ru,
                        type: "tel",
                        inputMode: "numeric",
                        autoComplete: "tel-national",
                        placeholder: "(555) 123-4567",
                        value: lr(r),
                        onChange: of,
                        onKeyDown: h => {
                            h.key === "Enter" && a && fu()
                        }
                        ,
                        style: ce.phoneInput,
                        autoFocus: !0
                    }), s.jsxs("label", {
                        style: {
                            display: "flex",
                            alignItems: "center",
                            gap: "6px",
                            marginTop: "8px",
                            paddingLeft: "16px",
                            cursor: "pointer",
                            userSelect: "none"
                        },
                        children: [s.jsx("input", {
                            type: "checkbox",
                            checked: Xr,
                            onChange: h => Jd(h.target.checked),
                            style: {
                                accentColor: V,
                                width: "14px",
                                height: "14px",
                                flexShrink: 0,
                                opacity: .7
                            }
                        }), s.jsx("span", {
                            style: {
                                fontFamily: k,
                                fontSize: "12px",
                                color: M,
                                opacity: .7
                            },
                            children: "I want to text Penny AI"
                        })]
                    })]
                }), u && s.jsx("p", {
                    style: ce.error,
                    children: u
                }), s.jsx("button", {
                    onClick: fu,
                    disabled: !a || !Xr || f,
                    style: {
                        ...ce.button,
                        opacity: a && Xr && !f ? 1 : .4,
                        cursor: a && Xr && !f ? "pointer" : "default"
                    },
                    children: f ? "Sending…" : "Send Code"
                }), s.jsx(Ea, {})]
            })
        })
    }
    if (e === "code")
        return s.jsx("div", {
            style: ce.container,
            children: s.jsxs("div", {
                style: ce.card,
                children: [s.jsx(ei, {}), s.jsx("h1", {
                    style: ce.wordmark,
                    children: "Shared shopping list"
                }), s.jsx("p", {
                    style: ce.codePrompt,
                    children: "Enter the code sent to"
                }), s.jsx("button", {
                    onClick: () => {
                        n("phone"),
                        c("")
                    }
                    ,
                    style: ce.phoneDisplay,
                    children: lr(r)
                }), s.jsx("div", {
                    style: ce.codeRow,
                    children: o.map( (a, h) => s.jsx("input", {
                        ref: x => {
                            Yt.current[h] = x
                        }
                        ,
                        type: "text",
                        inputMode: "numeric",
                        pattern: "[0-9]*",
                        autoComplete: h === 0 ? "one-time-code" : "off",
                        maxLength: 1,
                        value: a,
                        onChange: x => sf(h, x.target.value),
                        onKeyDown: x => uf(h, x),
                        onPaste: h === 0 ? af : void 0,
                        disabled: f,
                        style: {
                            ...ce.codeBox,
                            borderColor: a ? O : V,
                            ...f ? {
                                opacity: .5
                            } : {}
                        }
                    }, h))
                }), f && s.jsx("p", {
                    style: ce.verifying,
                    children: "Verifying…"
                }), u && s.jsx("p", {
                    style: ce.error,
                    children: u
                }), s.jsx(Ea, {})]
            })
        });
    const zo = a => s.jsxs("div", {
        style: {
            position: "relative"
        },
        children: [s.jsx("button", {
            onClick: () => lt(!Ys),
            style: z.hamburgerBtn,
            children: s.jsx("svg", {
                width: "20",
                height: "20",
                viewBox: "0 0 20 20",
                fill: "none",
                children: s.jsx("path", {
                    d: "M3 5h14M3 10h14M3 15h14",
                    stroke: Q,
                    strokeWidth: "1.8",
                    strokeLinecap: "round"
                })
            })
        }), Ys && s.jsxs(s.Fragment, {
            children: [s.jsx("div", {
                style: z.menuOverlay,
                onClick: () => lt(!1)
            }), s.jsxs("div", {
                style: z.menuDropdown,
                children: [s.jsx("button", {
                    style: z.menuItem(a === "home"),
                    onClick: () => {
                        lt(!1),
                        n("home")
                    }
                    ,
                    children: "Shopping List"
                }), s.jsx("button", {
                    style: z.menuItem(a === "saved"),
                    onClick: () => {
                        lt(!1),
                        n("saved")
                    }
                    ,
                    children: "Saved Lists"
                }), s.jsx("button", {
                    style: z.menuItem(a === "about"),
                    onClick: () => {
                        lt(!1),
                        n("about")
                    }
                    ,
                    children: "How to text Penny"
                }), s.jsx("button", {
                    style: z.menuItem(a === "settings-family"),
                    onClick: () => {
                        lt(!1),
                        n("settings-family")
                    }
                    ,
                    children: "Manage Household"
                }), s.jsx("button", {
                    style: z.menuItem(a === "settings-share"),
                    onClick: () => {
                        lt(!1),
                        n("settings-share")
                    }
                    ,
                    children: "Share & Earn"
                }), s.jsx("button", {
                    style: z.menuItem(a === "settings" || a === "settings-profile"),
                    onClick: () => {
                        lt(!1),
                        n("settings")
                    }
                    ,
                    children: "Settings"
                }), Yd && s.jsx("button", {
                    style: z.menuItem(a === "admin"),
                    onClick: () => {
                        lt(!1),
                        n("admin")
                    }
                    ,
                    children: "Dashboard"
                }), s.jsx("div", {
                    style: {
                        height: "1px",
                        backgroundColor: V,
                        margin: "4px 0"
                    }
                }), s.jsx("button", {
                    style: z.menuItem(!1),
                    onClick: hu,
                    children: "Sign Out"
                })]
            })]
        })]
    })
      , pf = () => bs.map( (a, h) => s.jsxs("div", {
        style: {
            display: "flex",
            alignItems: "center",
            padding: "10px 0",
            borderBottom: `1px solid ${V}`,
            gap: "10px"
        },
        children: [s.jsx("div", {
            style: {
                width: "32px",
                height: "32px",
                borderRadius: "50%",
                backgroundColor: O,
                color: X,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontFamily: k,
                fontSize: "14px",
                fontWeight: 600,
                flexShrink: 0
            },
            children: (a.name || a.phone || "?")[0].toUpperCase()
        }), s.jsxs("div", {
            children: [s.jsx("div", {
                style: {
                    fontFamily: k,
                    fontSize: "15px",
                    color: Q
                },
                children: a.name || lr(a.phone)
            }), a.name && s.jsx("div", {
                style: {
                    fontFamily: k,
                    fontSize: "13px",
                    color: M
                },
                children: lr(a.phone)
            })]
        })]
    }, h))
      , Xt = () => U ? s.jsxs("div", {
        style: {
            position: "fixed",
            top: "72px",
            left: "16px",
            right: "16px",
            display: "flex",
            alignItems: "center",
            gap: "10px",
            backgroundColor: U.type === "error" ? "#FEE2E2" : X,
            color: U.type === "error" ? "#991B1B" : Q,
            padding: "12px 16px",
            borderRadius: "16px",
            fontFamily: k,
            fontSize: "15px",
            fontWeight: 500,
            zIndex: 50,
            boxShadow: "0 4px 16px rgba(0,0,0,0.18)",
            border: `1px solid ${U.type === "error" ? "#FECACA" : V}`
        },
        children: [s.jsx(ti, {
            size: 32
        }), U.message]
    }) : null
      , Jr = (a, h) => s.jsx("div", {
        style: {
            flexShrink: 0,
            backgroundColor: X,
            borderBottom: `1px solid ${V}`
        },
        children: s.jsxs("div", {
            style: {
                display: "flex",
                alignItems: "center",
                padding: "16px 20px",
                position: "relative"
            },
            children: [s.jsx("span", {
                style: {
                    ...z.headerWordmark,
                    cursor: "pointer",
                    fontSize: "17px",
                    fontWeight: 700
                },
                onClick: () => n("home"),
                children: "thriftly"
            }), s.jsx("span", {
                style: {
                    position: "absolute",
                    left: "50%",
                    transform: "translateX(-50%)",
                    fontFamily: k,
                    fontSize: "15px",
                    fontWeight: 600,
                    color: Q
                },
                children: a
            }), s.jsx("div", {
                style: {
                    marginLeft: "auto"
                },
                children: zo(h)
            })]
        })
    })
      , _o = (a, h) => s.jsx("div", {
        style: {
            flexShrink: 0,
            backgroundColor: X,
            borderBottom: `1px solid ${V}`
        },
        children: s.jsxs("div", {
            style: {
                display: "flex",
                alignItems: "center",
                padding: "16px 20px"
            },
            children: [s.jsx("button", {
                onClick: () => n(h),
                style: {
                    background: "none",
                    border: "none",
                    cursor: "pointer",
                    padding: "4px 8px 4px 0",
                    color: O,
                    fontSize: "20px",
                    fontWeight: 600,
                    display: "flex",
                    alignItems: "center"
                },
                children: s.jsx("svg", {
                    width: "20",
                    height: "20",
                    viewBox: "0 0 20 20",
                    fill: "none",
                    children: s.jsx("path", {
                        d: "M13 4l-6 6 6 6",
                        stroke: O,
                        strokeWidth: "2",
                        strokeLinecap: "round",
                        strokeLinejoin: "round"
                    })
                })
            }), s.jsx("span", {
                style: {
                    fontFamily: k,
                    fontSize: "17px",
                    fontWeight: 600,
                    color: Q
                },
                children: a
            }), s.jsx("div", {
                style: {
                    marginLeft: "auto"
                },
                children: zo(h)
            })]
        })
    });
    if (e === "settings") {
        const a = [{
            label: "Profile",
            target: "settings-profile"
        }];
        return s.jsxs("div", {
            style: z.page,
            children: [Jr("Settings", "settings"), s.jsxs("div", {
                style: z.listArea,
                children: [a.map(h => s.jsxs("button", {
                    onClick: () => n(h.target),
                    style: {
                        display: "flex",
                        alignItems: "center",
                        width: "100%",
                        padding: "16px 20px",
                        background: "none",
                        border: "none",
                        borderBottom: `1px solid ${V}`,
                        cursor: "pointer",
                        textAlign: "left",
                        WebkitTapHighlightColor: "transparent"
                    },
                    children: [s.jsx("span", {
                        style: {
                            flex: 1,
                            fontFamily: k,
                            fontSize: "16px",
                            fontWeight: 500,
                            color: Q
                        },
                        children: h.label
                    }), s.jsx("span", {
                        style: {
                            color: M,
                            fontSize: "18px"
                        },
                        children: "›"
                    })]
                }, h.label)), s.jsx("button", {
                    onClick: hu,
                    style: {
                        display: "flex",
                        alignItems: "center",
                        width: "100%",
                        padding: "16px 20px",
                        background: "none",
                        border: "none",
                        borderBottom: `1px solid ${V}`,
                        cursor: "pointer",
                        textAlign: "left",
                        WebkitTapHighlightColor: "transparent"
                    },
                    children: s.jsx("span", {
                        style: {
                            flex: 1,
                            fontFamily: k,
                            fontSize: "16px",
                            fontWeight: 500,
                            color: nn
                        },
                        children: "Sign Out"
                    })
                })]
            }), Xt()]
        })
    }
    if (e === "settings-profile")
        return s.jsxs("div", {
            style: z.page,
            children: [_o("Profile", "settings"), s.jsx("div", {
                style: z.listArea,
                children: s.jsxs("div", {
                    style: {
                        padding: "20px",
                        display: "flex",
                        flexDirection: "column",
                        gap: "12px"
                    },
                    children: [s.jsxs("div", {
                        children: [s.jsx("label", {
                            style: z.fieldLabel,
                            children: "Name"
                        }), s.jsx("input", {
                            type: "text",
                            value: Js,
                            onChange: a => Zs(a.target.value),
                            placeholder: "Your name",
                            style: z.sheetTextInput
                        })]
                    }), s.jsxs("div", {
                        children: [s.jsx("label", {
                            style: z.fieldLabel,
                            children: "Email"
                        }), s.jsx("input", {
                            type: "email",
                            value: xo,
                            onChange: a => qs(a.target.value),
                            placeholder: "your@email.com",
                            style: z.sheetTextInput
                        }), s.jsx("p", {
                            style: {
                                fontFamily: k,
                                fontSize: "12px",
                                color: M,
                                marginTop: "4px",
                                paddingLeft: "4px"
                            },
                            children: "Set your email to add items by emailing penny@list.thrift.ly"
                        })]
                    }), s.jsx("button", {
                        onClick: cf,
                        disabled: Qr,
                        style: {
                            ...z.sheetButton,
                            opacity: Qr ? .5 : 1
                        },
                        children: Qr ? "Saving..." : "Save"
                    })]
                })
            }), Xt()]
        });
    if (e === "settings-family")
        return s.jsxs("div", {
            style: z.page,
            children: [s.jsx(li, {
                open: !!B,
                title: (B == null ? void 0 : B.title) || "",
                message: B == null ? void 0 : B.message,
                confirmLabel: B == null ? void 0 : B.confirmLabel,
                destructive: B == null ? void 0 : B.destructive,
                onConfirm: vo,
                onCancel: Vr
            }), _o("Manage Household", "home"), s.jsx("div", {
                style: z.listArea,
                children: s.jsxs("div", {
                    style: {
                        padding: "20px",
                        display: "flex",
                        flexDirection: "column",
                        gap: "20px"
                    },
                    children: [bs.length > 0 && s.jsxs("div", {
                        children: [s.jsx(ml, {
                            label: "Household Members"
                        }), pf(), s.jsx("button", {
                            onClick: () => go({
                                title: "Leave Household",
                                message: "You will be removed from this household.",
                                confirmLabel: "Leave",
                                destructive: !0,
                                onConfirm: () => {
                                    fetch("/api/settings/leave-household", {
                                        method: "POST"
                                    }).then(a => {
                                        a.ok ? (J("Left household"),
                                        iu()) : a.json().then(h => J((h == null ? void 0 : h.error) || "Failed", "error")).catch( () => J("Failed", "error"))
                                    }
                                    ).catch( () => J("Network error", "error"))
                                }
                            }),
                            style: {
                                marginTop: "12px",
                                padding: "10px",
                                fontFamily: k,
                                fontSize: "14px",
                                fontWeight: 500,
                                color: nn,
                                backgroundColor: "transparent",
                                border: `1px solid ${nn}`,
                                borderRadius: "10px",
                                cursor: "pointer",
                                width: "100%"
                            },
                            children: "Leave Household"
                        })]
                    }), s.jsxs("div", {
                        children: [s.jsx(ml, {
                            label: "Invite"
                        }), s.jsx("p", {
                            style: {
                                fontFamily: k,
                                fontSize: "15px",
                                color: M,
                                margin: "0 0 12px 0"
                            },
                            children: "Invite household members to share your shopping list."
                        }), s.jsx("button", {
                            onClick: ff,
                            disabled: Kr,
                            style: {
                                ...z.sheetButton,
                                opacity: Kr ? .5 : 1
                            },
                            children: Kr ? "Creating..." : "Text Invite Link"
                        })]
                    })]
                })
            }), Xt()]
        });
    if (e === "settings-share") {
        const a = () => {
            const x = `Try Thriftly — Penny AI helps your family organize the grocery list. Just text, email, or snap a photo and she handles the rest! ${`https://app.thrift.ly/r/${Vd}`}`;
            navigator.share ? navigator.share({
                title: "Thriftly",
                text: x
            }).catch( () => {}
            ) : window.open(`sms:?&body=${encodeURIComponent(x)}`, "_self")
        }
        ;
        return s.jsxs("div", {
            style: z.page,
            children: [_o("Share & Earn", "home"), s.jsx("div", {
                style: z.listArea,
                children: s.jsxs("div", {
                    style: {
                        padding: "24px 20px",
                        display: "flex",
                        flexDirection: "column",
                        gap: "20px"
                    },
                    children: [s.jsx("div", {
                        style: {
                            backgroundColor: Fe,
                            borderRadius: "12px",
                            padding: "16px",
                            textAlign: "center"
                        },
                        children: s.jsx("p", {
                            style: {
                                fontFamily: k,
                                fontSize: "15px",
                                color: Q,
                                margin: 0,
                                lineHeight: 1.6
                            },
                            children: "Share Thriftly with friends and family. The more people who use Penny, the better deals everyone gets."
                        })
                    }), s.jsx("button", {
                        onClick: a,
                        style: z.sheetButton,
                        children: "Share Your Link"
                    }), yn.length > 0 && s.jsxs("div", {
                        style: {
                            backgroundColor: Fe,
                            borderRadius: "12px",
                            padding: "12px 16px",
                            textAlign: "center"
                        },
                        children: [s.jsx("span", {
                            style: {
                                fontFamily: k,
                                fontSize: "24px",
                                fontWeight: 700,
                                color: O
                            },
                            children: yn.length
                        }), s.jsx("span", {
                            style: {
                                fontFamily: k,
                                fontSize: "14px",
                                color: M,
                                marginLeft: "8px"
                            },
                            children: yn.length === 1 ? "friend joined" : "friends joined"
                        })]
                    }), s.jsxs("div", {
                        style: {
                            backgroundColor: Fe,
                            borderRadius: "12px",
                            padding: "16px"
                        },
                        children: [s.jsx("p", {
                            style: {
                                fontFamily: k,
                                fontSize: "15px",
                                fontWeight: 600,
                                color: Q,
                                margin: "0 0 8px 0"
                            },
                            children: "Exclusive Rebates — Coming Soon"
                        }), s.jsx("p", {
                            style: {
                                fontFamily: k,
                                fontSize: "14px",
                                color: M,
                                margin: "0 0 12px 0",
                                lineHeight: 1.5
                            },
                            children: "We're partnering with brands to offer exclusive rebates on the things you already buy. No points, no gimmicks — real savings on real groceries."
                        }), s.jsx("p", {
                            style: {
                                fontFamily: k,
                                fontSize: "13px",
                                color: M,
                                margin: "0 0 8px 0",
                                lineHeight: 1.5
                            },
                            children: "Are you a product manager at a CPG brand? Get your products in front of engaged shoppers."
                        }), s.jsx("a", {
                            href: "mailto:partners@thrift.ly?subject=Create%20a%20brand%20deal",
                            style: {
                                fontFamily: k,
                                fontSize: "13px",
                                color: O,
                                textDecoration: "underline",
                                textUnderlineOffset: "2px"
                            },
                            children: "Create a brand deal"
                        })]
                    }), yn.length > 0 && s.jsxs("div", {
                        children: [s.jsx(ml, {
                            label: `Friends (${yn.length})`
                        }), yn.map( (h, x) => s.jsxs("div", {
                            style: {
                                display: "flex",
                                alignItems: "center",
                                padding: "10px 0",
                                borderBottom: `1px solid ${V}`,
                                gap: "10px"
                            },
                            children: [s.jsx("div", {
                                style: {
                                    width: "32px",
                                    height: "32px",
                                    borderRadius: "50%",
                                    backgroundColor: O,
                                    color: X,
                                    display: "flex",
                                    alignItems: "center",
                                    justifyContent: "center",
                                    fontFamily: k,
                                    fontSize: "14px",
                                    fontWeight: 600,
                                    flexShrink: 0
                                },
                                children: (h.name || "?")[0].toUpperCase()
                            }), s.jsxs("div", {
                                style: {
                                    flex: 1
                                },
                                children: [s.jsx("div", {
                                    style: {
                                        fontFamily: k,
                                        fontSize: "15px",
                                        color: Q
                                    },
                                    children: h.name || "Friend"
                                }), s.jsx("div", {
                                    style: {
                                        fontFamily: k,
                                        fontSize: "13px",
                                        color: M
                                    },
                                    children: new Date(h.created_at).toLocaleDateString()
                                })]
                            })]
                        }, x))]
                    })]
                })
            }), Xt()]
        })
    }
    if (e === "about")
        return s.jsxs("div", {
            style: z.page,
            children: [Jr("How to text Penny", "about"), s.jsx("div", {
                style: z.listArea,
                children: s.jsxs("div", {
                    style: {
                        padding: "30px 20px",
                        display: "flex",
                        flexDirection: "column",
                        alignItems: "center",
                        gap: "24px"
                    },
                    children: [s.jsx(ti, {
                        size: 96
                    }), s.jsx("div", {
                        style: {
                            width: "100%"
                        },
                        children: s.jsxs("ol", {
                            style: {
                                fontFamily: k,
                                fontSize: "15px",
                                color: Q,
                                margin: 0,
                                paddingLeft: "24px",
                                lineHeight: "1.8"
                            },
                            children: [s.jsxs("li", {
                                style: {
                                    marginBottom: "8px"
                                },
                                children: [s.jsx("strong", {
                                    children: "Add Penny to your contacts"
                                }), " using the button below"]
                            }), s.jsxs("li", {
                                style: {
                                    marginBottom: "8px"
                                },
                                children: [s.jsx("strong", {
                                    children: "Text her what you need"
                                }), " — a grocery list, a photo of your fridge, pantry, or a recipe"]
                            }), s.jsxs("li", {
                                children: [s.jsx("strong", {
                                    children: "She adds it to your list"
                                }), " — works in group chats with your family too"]
                            })]
                        })
                    }), s.jsx("p", {
                        style: {
                            fontFamily: k,
                            fontSize: "13px",
                            color: M,
                            textAlign: "center",
                            margin: 0,
                            lineHeight: "1.5"
                        },
                        children: "Penny's shy — she won't text back yet. But don't worry, your items will appear on your list!"
                    }), s.jsx("a", {
                        href: "/api/penny.vcf",
                        style: {
                            display: "block",
                            width: "100%",
                            textAlign: "center",
                            padding: "13px",
                            fontFamily: k,
                            fontSize: "15px",
                            fontWeight: 600,
                            color: X,
                            backgroundColor: O,
                            borderRadius: "12px",
                            textDecoration: "none",
                            cursor: "pointer",
                            border: "none",
                            boxSizing: "border-box"
                        },
                        children: "Add Penny to Contacts"
                    }), !xo && s.jsx("p", {
                        style: {
                            fontFamily: k,
                            fontSize: "12px",
                            color: M,
                            textAlign: "center",
                            margin: 0
                        },
                        children: "Set your email in Settings to email Penny"
                    }), s.jsxs("div", {
                        style: {
                            width: "100%",
                            backgroundColor: Fe,
                            borderRadius: "12px",
                            padding: "16px 20px"
                        },
                        children: [s.jsx("p", {
                            style: {
                                fontFamily: k,
                                fontSize: "15px",
                                fontWeight: 600,
                                color: Q,
                                margin: "0 0 10px 0"
                            },
                            children: "Coming Soon"
                        }), s.jsxs("ul", {
                            style: {
                                fontFamily: k,
                                fontSize: "14px",
                                color: M,
                                margin: 0,
                                paddingLeft: "20px",
                                lineHeight: "1.8"
                            },
                            children: [s.jsx("li", {
                                children: "Best deals near you"
                            }), s.jsx("li", {
                                children: "Best places to shop"
                            }), s.jsx("li", {
                                children: "Delivery options"
                            })]
                        }), s.jsx("a", {
                            href: "mailto:support@thrift.ly?subject=Feature%20request",
                            style: {
                                fontFamily: k,
                                fontSize: "13px",
                                color: O,
                                marginTop: "12px",
                                display: "inline-block",
                                textDecoration: "underline",
                                textUnderlineOffset: "2px"
                            },
                            children: "Request a feature"
                        })]
                    })]
                })
            }), Xt()]
        });
    if (e === "saved")
        return s.jsxs("div", {
            style: z.page,
            children: [s.jsx(li, {
                open: !!B,
                title: (B == null ? void 0 : B.title) || "",
                message: B == null ? void 0 : B.message,
                confirmLabel: B == null ? void 0 : B.confirmLabel,
                destructive: B == null ? void 0 : B.destructive,
                onConfirm: vo,
                onCancel: Vr
            }), Jr("Saved Lists", "saved"), s.jsx("div", {
                style: z.listArea,
                children: Xs.length === 0 ? s.jsxs("div", {
                    style: z.emptyState,
                    children: [s.jsx("p", {
                        style: z.emptyText,
                        children: "No saved lists yet."
                    }), s.jsx("p", {
                        style: z.emptySubtext,
                        children: "Save your current list to reuse it later."
                    })]
                }) : Xs.map(a => s.jsxs("button", {
                    onClick: () => Hr(a),
                    style: {
                        display: "flex",
                        alignItems: "center",
                        width: "100%",
                        padding: "14px 20px",
                        background: "none",
                        border: "none",
                        borderBottom: `1px solid ${V}`,
                        cursor: "pointer",
                        textAlign: "left",
                        WebkitTapHighlightColor: "transparent",
                        gap: "12px"
                    },
                    children: [s.jsxs("div", {
                        style: {
                            flex: 1
                        },
                        children: [s.jsx("div", {
                            style: {
                                fontFamily: k,
                                fontSize: "16px",
                                fontWeight: 500,
                                color: Q
                            },
                            children: a.name
                        }), s.jsxs("div", {
                            style: {
                                fontFamily: k,
                                fontSize: "13px",
                                color: M,
                                marginTop: "2px"
                            },
                            children: [a.item_count, " item", a.item_count !== 1 ? "s" : "", " · ", new Date(a.created_at).toLocaleDateString()]
                        })]
                    }), s.jsx("span", {
                        style: {
                            color: M,
                            fontSize: "18px"
                        },
                        children: "›"
                    })]
                }, a.id))
            }), Xt(), Et && s.jsxs(hl, {
                isOpen: !0,
                onClose: () => Hr(null),
                title: Et.name,
                children: [s.jsxs("p", {
                    style: {
                        fontFamily: k,
                        fontSize: "14px",
                        color: M,
                        margin: "0 0 8px 0"
                    },
                    children: [Et.item_count, " item", Et.item_count !== 1 ? "s" : ""]
                }), s.jsx("button", {
                    onClick: () => du(Et.id, "overwrite"),
                    style: z.sheetButton,
                    children: "Replace Current List"
                }), s.jsx("button", {
                    onClick: () => du(Et.id, "merge"),
                    style: {
                        ...z.sheetButton,
                        backgroundColor: "transparent",
                        color: O,
                        border: `1.5px solid ${O}`
                    },
                    children: "Merge into Current List"
                }), s.jsx("button", {
                    onClick: () => go({
                        title: "Delete List",
                        message: `Delete "${Et.name}"? This cannot be undone.`,
                        confirmLabel: "Delete",
                        destructive: !0,
                        onConfirm: () => lf(Et.id)
                    }),
                    style: z.sheetDeleteBtn,
                    children: "Delete List"
                })]
            })]
        });
    if (e === "admin") {
        const a = [7, 30, 90];
        return s.jsxs("div", {
            style: z.page,
            children: [Jr("Dashboard", "admin"), s.jsxs("div", {
                style: {
                    ...z.listArea,
                    padding: "20px 16px"
                },
                children: [s.jsx("div", {
                    style: {
                        display: "flex",
                        gap: "8px",
                        marginBottom: "20px"
                    },
                    children: a.map(h => s.jsxs("button", {
                        onClick: () => Gd(h),
                        style: {
                            flex: 1,
                            padding: "8px",
                            borderRadius: "8px",
                            border: `1px solid ${V}`,
                            backgroundColor: Yr === h ? O : X,
                            color: Yr === h ? X : Q,
                            fontFamily: k,
                            fontSize: "14px",
                            fontWeight: 600,
                            cursor: "pointer"
                        },
                        children: [h, "d"]
                    }, h))
                }), Kt ? s.jsxs(s.Fragment, {
                    children: [s.jsx("div", {
                        style: {
                            display: "grid",
                            gridTemplateColumns: "1fr 1fr",
                            gap: "12px",
                            marginBottom: "24px"
                        },
                        children: [{
                            label: "Active Users",
                            value: Kt.active_users
                        }, {
                            label: "Total Users",
                            value: Kt.total_users
                        }, {
                            label: "New Users",
                            value: Kt.new_users
                        }, {
                            label: "K-Factor",
                            value: Kt.k_factor.toFixed(2)
                        }].map(h => s.jsxs("div", {
                            style: {
                                backgroundColor: X,
                                borderRadius: "12px",
                                padding: "16px",
                                border: `1px solid ${V}`
                            },
                            children: [s.jsx("div", {
                                style: {
                                    fontFamily: k,
                                    fontSize: "13px",
                                    color: M,
                                    marginBottom: "4px"
                                },
                                children: h.label
                            }), s.jsx("div", {
                                style: {
                                    fontFamily: k,
                                    fontSize: "28px",
                                    fontWeight: 700,
                                    color: Q
                                },
                                children: h.value
                            })]
                        }, h.label))
                    }), s.jsx("div", {
                        style: {
                            fontFamily: k,
                            fontSize: "16px",
                            fontWeight: 600,
                            color: Q,
                            marginBottom: "12px"
                        },
                        children: "Referral Leaderboard"
                    }), Kt.leaderboard.length === 0 ? s.jsx("div", {
                        style: {
                            fontFamily: k,
                            fontSize: "14px",
                            color: M
                        },
                        children: "No referrals yet."
                    }) : Kt.leaderboard.map( (h, x) => s.jsxs("div", {
                        style: {
                            display: "flex",
                            justifyContent: "space-between",
                            alignItems: "center",
                            padding: "12px 0",
                            borderBottom: `1px solid ${V}`
                        },
                        children: [s.jsxs("div", {
                            children: [s.jsx("div", {
                                style: {
                                    fontFamily: k,
                                    fontSize: "15px",
                                    color: Q
                                },
                                children: h.name || h.phone
                            }), h.name && s.jsx("div", {
                                style: {
                                    fontFamily: k,
                                    fontSize: "13px",
                                    color: M
                                },
                                children: h.phone
                            })]
                        }), s.jsxs("div", {
                            style: {
                                textAlign: "right"
                            },
                            children: [s.jsxs("div", {
                                style: {
                                    fontFamily: k,
                                    fontSize: "15px",
                                    fontWeight: 600,
                                    color: O
                                },
                                children: [h.points, " pts"]
                            }), s.jsxs("div", {
                                style: {
                                    fontFamily: k,
                                    fontSize: "13px",
                                    color: M
                                },
                                children: [h.referrals, " referrals"]
                            })]
                        })]
                    }, x))]
                }) : s.jsx("div", {
                    style: {
                        fontFamily: k,
                        fontSize: "14px",
                        color: M,
                        textAlign: "center",
                        padding: "40px 0"
                    },
                    children: "Loading..."
                })]
            }), Xt()]
        })
    }
    const hf = a => {
        if (m === a) {
            S(null);
            return
        }
        S(a),
        setTimeout( () => {
            var h;
            (h = ne.current[a]) == null || h.scrollIntoView({
                behavior: "smooth",
                block: "start"
            })
        }
        , 0)
    }
      , mf = ja.filter(a => C.some(h => h.department === a));
    return s.jsxs("div", {
        style: z.page,
        children: [s.jsx(li, {
            open: !!B,
            title: (B == null ? void 0 : B.title) || "",
            message: B == null ? void 0 : B.message,
            confirmLabel: B == null ? void 0 : B.confirmLabel,
            destructive: B == null ? void 0 : B.destructive,
            onConfirm: vo,
            onCancel: Vr
        }), s.jsxs("div", {
            style: {
                flexShrink: 0,
                backgroundColor: X,
                borderBottom: `1px solid ${V}`
            },
            children: [s.jsxs("div", {
                style: {
                    display: "flex",
                    alignItems: "center",
                    padding: "10px 16px",
                    position: "relative"
                },
                children: [s.jsx("span", {
                    style: {
                        ...z.headerWordmark,
                        cursor: "pointer",
                        fontSize: "17px",
                        fontWeight: 700
                    },
                    onClick: () => n("home"),
                    children: "thriftly"
                }), s.jsx("span", {
                    style: {
                        position: "absolute",
                        left: "50%",
                        transform: "translateX(-50%)",
                        fontFamily: k,
                        fontSize: "15px",
                        fontWeight: 600,
                        color: Q
                    },
                    children: "Shopping List"
                }), s.jsx("div", {
                    style: {
                        marginLeft: "auto"
                    },
                    children: zo("home")
                })]
            }), C.length > 0 && ( () => {
                const a = Math.round(C.filter(h => h.checked).length / C.length * 100);
                return s.jsx("div", {
                    style: {
                        height: "3px",
                        backgroundColor: V
                    },
                    children: s.jsx("div", {
                        style: {
                            height: "100%",
                            width: `${a}%`,
                            backgroundColor: O,
                            borderRadius: "0 2px 2px 0",
                            transition: "width 0.3s ease"
                        }
                    })
                })
            }
            )()]
        }), s.jsxs("div", {
            style: z.listArea,
            children: [p && s.jsx("div", {
                style: {
                    position: "absolute",
                    inset: 0,
                    backgroundColor: "rgba(0,0,0,0.04)",
                    zIndex: 10,
                    pointerEvents: "auto"
                }
            }), C.length === 0 ? s.jsxs("div", {
                style: z.emptyState,
                children: [s.jsx("p", {
                    style: z.emptyText,
                    children: "Your list is empty."
                }), s.jsx("p", {
                    style: z.emptySubtext,
                    children: "Tell Penny what you need."
                })]
            }) : mf.map(a => {
                const h = C.filter(D => D.department === a)
                  , x = h.filter(D => D.checked).length
                  , P = x === h.length
                  , K = m === a;
                return s.jsxs("div", {
                    ref: D => {
                        ne.current[a] = D
                    }
                    ,
                    children: [s.jsxs("button", {
                        style: z.deptHeader(K),
                        onClick: () => hf(a),
                        children: [P && s.jsx("span", {
                            style: {
                                color: O,
                                fontSize: "14px",
                                marginRight: "2px"
                            },
                            children: "✓"
                        }), s.jsx("span", {
                            style: P ? {
                                textDecoration: "line-through",
                                opacity: .5
                            } : void 0,
                            children: a
                        }), s.jsxs("span", {
                            style: z.deptCount,
                            children: [x, "/", h.length]
                        }), s.jsx("span", {
                            style: z.deptChevron(K),
                            children: "›"
                        })]
                    }), K && h.map(D => s.jsxs("div", {
                        style: z.itemRow,
                        children: [s.jsx("button", {
                            onClick: () => su(D.id),
                            style: z.itemCheckBtn,
                            children: s.jsx("span", {
                                style: z.itemCheck(D.checked),
                                children: D.checked && "✓"
                            })
                        }), s.jsxs("div", {
                            style: z.itemCenter,
                            onClick: () => su(D.id),
                            children: [s.jsxs("span", {
                                style: z.itemName(D.checked),
                                children: [D.brand ? `${D.brand} ` : "", D.name]
                            }), (D.quantity > 1 || D.size) && s.jsxs("span", {
                                style: z.itemMeta,
                                children: [D.quantity > 1 ? `×${D.quantity}` : "", D.quantity > 1 && D.size ? " · " : "", D.size]
                            })]
                        }), s.jsx("button", {
                            onClick: () => tf(D),
                            style: z.itemEditBtn,
                            children: s.jsx("span", {
                                style: {
                                    width: "32px",
                                    height: "32px",
                                    borderRadius: "50%",
                                    backgroundColor: Fe,
                                    display: "flex",
                                    alignItems: "center",
                                    justifyContent: "center"
                                },
                                children: s.jsxs("svg", {
                                    width: "16",
                                    height: "16",
                                    viewBox: "0 0 16 16",
                                    fill: "none",
                                    children: [s.jsx("path", {
                                        d: "M11.5 1.5a1.77 1.77 0 0 1 2.5 0 1.77 1.77 0 0 1 0 2.5L5.5 12.5 1.5 14l1.5-4L11.5 1.5z",
                                        stroke: "currentColor",
                                        strokeWidth: "1.4",
                                        strokeLinecap: "round",
                                        strokeLinejoin: "round"
                                    }), s.jsx("path", {
                                        d: "M10 3.5l2.5 2.5",
                                        stroke: "currentColor",
                                        strokeWidth: "1.4",
                                        strokeLinecap: "round"
                                    })]
                                })
                            })
                        })]
                    }, D.id))]
                }, a)
            }
            )]
        }), C.length > 0 && s.jsxs("div", {
            style: {
                flexShrink: 0,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "16px",
                padding: "10px 16px",
                borderTop: `1px solid ${V}`
            },
            children: [s.jsx("button", {
                onClick: () => {
                    Ur(""),
                    $r(!0)
                }
                ,
                style: {
                    fontFamily: k,
                    fontSize: "14px",
                    fontWeight: 500,
                    color: M,
                    background: "none",
                    border: "none",
                    cursor: "pointer",
                    textDecoration: "underline",
                    textUnderlineOffset: "2px"
                },
                children: "Save List"
            }), s.jsx("button", {
                onClick: () => go({
                    title: "Clear List",
                    message: "Remove all items from your list?",
                    confirmLabel: "Clear",
                    destructive: !0,
                    onConfirm: au
                }),
                style: {
                    fontFamily: k,
                    fontSize: "14px",
                    fontWeight: 500,
                    color: M,
                    background: "none",
                    border: "none",
                    cursor: "pointer",
                    textDecoration: "underline",
                    textUnderlineOffset: "2px"
                },
                children: "Clear List"
            })]
        }), s.jsx("input", {
            ref: Ks,
            type: "file",
            accept: "image/*",
            onChange: ef,
            style: {
                display: "none"
            }
        }), ( () => {
            const a = Bd && C.length > 0 && C.every(re => re.checked);
            if (!(gn || U || a || Gr))
                return null;
            const x = a && !gn && !U && !Gr
              , P = !!Gr && !gn && !U && !x
              , K = x ? O : P ? `${O}12` : (U == null ? void 0 : U.type) === "error" ? "#FEE2E2" : "#F5F3EF"
              , D = x ? X : P ? O : (U == null ? void 0 : U.type) === "error" ? "#991B1B" : Q;
            return s.jsxs("div", {
                style: {
                    flexShrink: 0,
                    display: "flex",
                    alignItems: "center",
                    gap: P ? "8px" : "10px",
                    padding: P ? "8px 16px" : "10px 16px",
                    backgroundColor: K,
                    borderTop: `1px solid ${x ? O : P ? "transparent" : V}`,
                    fontFamily: k,
                    fontSize: "14px",
                    color: D,
                    fontWeight: 500
                },
                children: [s.jsx(ti, {
                    size: P ? 22 : 45
                }), x ? s.jsxs(s.Fragment, {
                    children: [s.jsxs("div", {
                        style: {
                            flex: 1
                        },
                        children: [s.jsx("div", {
                            style: {
                                marginBottom: "6px"
                            },
                            children: "You're done!"
                        }), s.jsxs("div", {
                            style: {
                                display: "flex",
                                gap: "12px"
                            },
                            children: [s.jsx("button", {
                                onClick: () => {
                                    hn(!1),
                                    Ur(""),
                                    $r(!0)
                                }
                                ,
                                style: {
                                    background: "rgba(255,255,255,0.2)",
                                    border: "none",
                                    color: X,
                                    fontFamily: k,
                                    fontSize: "13px",
                                    fontWeight: 600,
                                    cursor: "pointer",
                                    padding: "5px 12px",
                                    borderRadius: "12px"
                                },
                                children: "Save List"
                            }), s.jsx("button", {
                                onClick: () => {
                                    hn(!1),
                                    au()
                                }
                                ,
                                style: {
                                    background: "rgba(255,255,255,0.2)",
                                    border: "none",
                                    color: X,
                                    fontFamily: k,
                                    fontSize: "13px",
                                    fontWeight: 600,
                                    cursor: "pointer",
                                    padding: "5px 12px",
                                    borderRadius: "12px"
                                },
                                children: "Clear List"
                            })]
                        })]
                    }), s.jsx("button", {
                        onClick: () => hn(!1),
                        style: {
                            background: "none",
                            border: "none",
                            color: X,
                            fontFamily: k,
                            fontSize: "16px",
                            cursor: "pointer",
                            padding: "0",
                            opacity: .6,
                            alignSelf: "flex-start"
                        },
                        children: "×"
                    })]
                }) : P ? s.jsx("span", {
                    style: {
                        flex: 1,
                        fontSize: "13px"
                    },
                    children: Gr
                }) : s.jsxs(s.Fragment, {
                    children: [s.jsx("span", {
                        style: {
                            flex: 1
                        },
                        children: gn || (U == null ? void 0 : U.message)
                    }), gn && s.jsx("span", {
                        className: "penny-pulse",
                        style: {
                            width: "6px",
                            height: "6px",
                            borderRadius: "50%",
                            backgroundColor: O,
                            flexShrink: 0
                        }
                    }), !gn && U && s.jsxs(s.Fragment, {
                        children: [(Ee.length > 0 || He.length > 0) && U.type !== "error" && s.jsx("button", {
                            onClick: () => {
                                fn(!0),
                                dt(null),
                                je.current && clearTimeout(je.current)
                            }
                            ,
                            style: {
                                background: O,
                                border: "none",
                                color: X,
                                fontFamily: k,
                                fontSize: "13px",
                                fontWeight: 600,
                                cursor: "pointer",
                                padding: "4px 12px",
                                borderRadius: "12px",
                                flexShrink: 0
                            },
                            children: "Review"
                        }), s.jsx("button", {
                            onClick: () => {
                                dt(null),
                                je.current && clearTimeout(je.current)
                            }
                            ,
                            style: {
                                background: "none",
                                border: "none",
                                color: x ? X : M,
                                fontFamily: k,
                                fontSize: "18px",
                                cursor: "pointer",
                                padding: "0 2px",
                                lineHeight: 1,
                                flexShrink: 0
                            },
                            children: "×"
                        })]
                    })]
                })]
            })
        }
        )(), s.jsxs("div", {
            style: z.chatBar,
            children: [pn ? s.jsxs("div", {
                style: {
                    position: "relative",
                    flexShrink: 0
                },
                children: [s.jsx("img", {
                    src: pn,
                    alt: "Photo preview",
                    style: {
                        width: "40px",
                        height: "40px",
                        borderRadius: "8px",
                        objectFit: "cover"
                    }
                }), s.jsx("button", {
                    onClick: () => mo(null),
                    style: {
                        position: "absolute",
                        top: "-6px",
                        right: "-6px",
                        width: "18px",
                        height: "18px",
                        borderRadius: "50%",
                        backgroundColor: Q,
                        color: X,
                        border: "none",
                        fontSize: "11px",
                        lineHeight: "18px",
                        textAlign: "center",
                        cursor: "pointer",
                        padding: 0
                    },
                    children: "×"
                })]
            }) : s.jsx("button", {
                style: z.chatIconBtn,
                title: "Add photo",
                onClick: () => {
                    var a;
                    return (a = Ks.current) == null ? void 0 : a.click()
                }
                ,
                children: s.jsxs("svg", {
                    width: "22",
                    height: "22",
                    viewBox: "0 0 22 22",
                    fill: "none",
                    children: [s.jsx("rect", {
                        x: "1",
                        y: "5",
                        width: "20",
                        height: "14",
                        rx: "3",
                        stroke: M,
                        strokeWidth: "1.5"
                    }), s.jsx("circle", {
                        cx: "11",
                        cy: "12",
                        r: "3.5",
                        stroke: M,
                        strokeWidth: "1.5"
                    }), s.jsx("path", {
                        d: "M7 5l1.5-2h5L15 5",
                        stroke: M,
                        strokeWidth: "1.5",
                        strokeLinecap: "round",
                        strokeLinejoin: "round"
                    })]
                })
            }), s.jsx("input", {
                type: "text",
                placeholder: "Tell Penny what you need…",
                value: _,
                onChange: a => Z(a.target.value),
                onKeyDown: a => {
                    a.key === "Enter" && uu()
                }
                ,
                disabled: p,
                style: z.chatInput
            }), s.jsx("button", {
                onClick: uu,
                disabled: !_.trim() && !pn || p,
                style: z.chatSendBtn((!!_.trim() || !!pn) && !p),
                children: p ? s.jsx("span", {
                    style: {
                        fontSize: "12px",
                        fontFamily: k
                    },
                    children: "…"
                }) : s.jsx("svg", {
                    width: "18",
                    height: "18",
                    viewBox: "0 0 18 18",
                    fill: "none",
                    children: s.jsx("path", {
                        d: "M2 9h14M10 3l6 6-6 6",
                        stroke: "currentColor",
                        strokeWidth: "1.8",
                        strokeLinecap: "round",
                        strokeLinejoin: "round"
                    })
                })
            })]
        }), E && s.jsxs(hl, {
            isOpen: !0,
            onClose: () => I(null),
            title: "Edit item",
            maxHeight: "75dvh",
            children: [s.jsxs("p", {
                style: {
                    fontFamily: k,
                    fontSize: "13px",
                    color: M,
                    margin: "-4px 0 8px 0"
                },
                children: [E.added_by_name || (E.added_by_phone ? lr(E.added_by_phone) : ""), (E.added_by_name || E.added_by_phone) && " · ", E.source === "sms" ? "Text" : E.source === "email" ? "Email" : "App", E.created_at && ` · ${new Date(E.created_at).toLocaleDateString()}`]
            }), s.jsxs("div", {
                children: [s.jsx("label", {
                    style: z.fieldLabel,
                    children: "Name"
                }), s.jsx("input", {
                    type: "text",
                    value: F,
                    onChange: a => R(a.target.value),
                    placeholder: "Item name",
                    style: z.sheetTextInput,
                    autoFocus: !0
                })]
            }), s.jsxs("div", {
                children: [s.jsx("label", {
                    style: z.fieldLabel,
                    children: "Brand"
                }), s.jsx("input", {
                    type: "text",
                    value: te,
                    onChange: a => $(a.target.value),
                    placeholder: "Optional",
                    style: z.sheetTextInput
                })]
            }), s.jsxs("div", {
                children: [s.jsx("label", {
                    style: z.fieldLabel,
                    children: "Department"
                }), s.jsx("select", {
                    value: Pe,
                    onChange: a => Ct(a.target.value),
                    style: z.sheetSelect,
                    children: ja.map(a => s.jsx("option", {
                        value: a,
                        children: a
                    }, a))
                })]
            }), s.jsxs("div", {
                style: z.sheetRow,
                children: [s.jsxs("div", {
                    style: {
                        flex: 1
                    },
                    children: [s.jsx("label", {
                        style: z.fieldLabel,
                        children: "Size"
                    }), s.jsx("input", {
                        type: "text",
                        list: "size-suggestions",
                        value: Br,
                        onChange: a => dn(a.target.value),
                        placeholder: "e.g. 16 oz, 1 lb",
                        style: z.sheetTextInput
                    }), s.jsx("datalist", {
                        id: "size-suggestions",
                        children: ["4 oz", "8 oz", "12 oz", "16 oz", "24 oz", "32 oz", "1 lb", "2 lb", "5 lb", "½ gal", "1 gal", "Small", "Medium", "Large", "XL"].map(a => s.jsx("option", {
                            value: a
                        }, a))
                    })]
                }), s.jsxs("div", {
                    children: [s.jsx("label", {
                        style: z.fieldLabel,
                        children: "Qty"
                    }), s.jsx(Yh, {
                        value: jt,
                        onChange: Xn
                    })]
                })]
            }), s.jsx("button", {
                onClick: nf,
                disabled: !F.trim() || rt,
                style: {
                    ...z.sheetButton,
                    opacity: F.trim() && !rt ? 1 : .4
                },
                children: rt ? "Saving…" : "Save"
            }), A.length > 0 && s.jsxs("div", {
                style: {
                    marginTop: "8px"
                },
                children: [s.jsx(ml, {
                    label: "History"
                }), A.map( (a, h) => s.jsxs("div", {
                    style: {
                        padding: "6px 0",
                        borderBottom: h < A.length - 1 ? `1px solid ${V}` : "none",
                        fontFamily: k,
                        fontSize: "13px",
                        color: M
                    },
                    children: [s.jsx("span", {
                        style: {
                            fontWeight: 500,
                            color: Q
                        },
                        children: a.user_name || "Unknown"
                    }), " ", a.action, a.detail ? ` (${a.detail})` : "", " · ", a.source === "sms" ? "Text" : a.source === "email" ? "Email" : "App", a.created_at && ` · ${new Date(a.created_at).toLocaleDateString()}`]
                }, h))]
            }), s.jsx("button", {
                onClick: rf,
                disabled: rt,
                style: z.sheetDeleteBtn,
                children: "Delete item"
            })]
        }), Wd && (Ee.length > 0 || He.length > 0) && s.jsxs(hl, {
            isOpen: !0,
            onClose: () => {
                fn(!1),
                xe([]),
                Gn([])
            }
            ,
            title: Ee.length > 0 ? "Added" : void 0,
            children: [Ee.length > 0 && s.jsx(s.Fragment, {
                children: Ee.map(a => s.jsxs("div", {
                    style: {
                        display: "flex",
                        alignItems: "center",
                        padding: "10px 0",
                        borderBottom: `1px solid ${V}`,
                        gap: "8px"
                    },
                    children: [s.jsxs("div", {
                        style: {
                            flex: 1
                        },
                        children: [s.jsxs("span", {
                            style: {
                                fontFamily: k,
                                fontSize: "16px",
                                color: Q
                            },
                            children: [a.brand ? `${a.brand} ` : "", a.name]
                        }), a.size && s.jsx("span", {
                            style: {
                                fontFamily: k,
                                fontSize: "13px",
                                color: M,
                                marginLeft: "6px"
                            },
                            children: a.size
                        }), s.jsx("div", {
                            style: {
                                fontFamily: k,
                                fontSize: "12px",
                                color: M,
                                marginTop: "2px"
                            },
                            children: a.department
                        })]
                    }), s.jsxs("div", {
                        style: {
                            display: "flex",
                            alignItems: "center",
                            gap: "0",
                            border: `1.5px solid ${V}`,
                            borderRadius: "10px",
                            overflow: "hidden",
                            backgroundColor: Fe,
                            flexShrink: 0
                        },
                        children: [s.jsx("button", {
                            onClick: async () => {
                                const h = Math.max(1, a.quantity - 1)
                                  , x = await fetch(`/api/list/${a.id}`, {
                                    method: "PATCH",
                                    headers: {
                                        "Content-Type": "application/json"
                                    },
                                    body: JSON.stringify({
                                        quantity: h
                                    })
                                });
                                if (x.ok) {
                                    const P = await x.json();
                                    xe(K => K.map(D => D.id === P.id ? P : D)),
                                    j(K => vn(K.map(D => D.id === P.id ? P : D)))
                                }
                            }
                            ,
                            style: {
                                width: "34px",
                                height: "34px",
                                border: "none",
                                background: "none",
                                fontSize: "18px",
                                color: O,
                                cursor: "pointer",
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center"
                            },
                            children: "−"
                        }), s.jsx("span", {
                            style: {
                                fontFamily: k,
                                fontSize: "15px",
                                fontWeight: 600,
                                color: Q,
                                minWidth: "24px",
                                textAlign: "center"
                            },
                            children: a.quantity
                        }), s.jsx("button", {
                            onClick: async () => {
                                const h = await fetch(`/api/list/${a.id}`, {
                                    method: "PATCH",
                                    headers: {
                                        "Content-Type": "application/json"
                                    },
                                    body: JSON.stringify({
                                        quantity: a.quantity + 1
                                    })
                                });
                                if (h.ok) {
                                    const x = await h.json();
                                    xe(P => P.map(K => K.id === x.id ? x : K)),
                                    j(P => vn(P.map(K => K.id === x.id ? x : K)))
                                }
                            }
                            ,
                            style: {
                                width: "34px",
                                height: "34px",
                                border: "none",
                                background: "none",
                                fontSize: "18px",
                                color: O,
                                cursor: "pointer",
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center"
                            },
                            children: "+"
                        })]
                    }), s.jsx("button", {
                        onClick: async () => {
                            await fetch(`/api/list/${a.id}`, {
                                method: "DELETE"
                            }),
                            j(x => x.filter(P => P.id !== a.id));
                            const h = Ee.filter(x => x.id !== a.id);
                            xe(h),
                            h.length === 0 && He.length === 0 && fn(!1)
                        }
                        ,
                        style: {
                            flexShrink: 0,
                            width: "28px",
                            height: "28px",
                            borderRadius: "50%",
                            border: `1px solid ${V}`,
                            background: "none",
                            color: M,
                            fontSize: "14px",
                            cursor: "pointer",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center"
                        },
                        children: "×"
                    })]
                }, a.id))
            }), He.length > 0 && s.jsxs(s.Fragment, {
                children: [s.jsx("p", {
                    style: {
                        ...z.sheetTitle,
                        marginTop: Ee.length > 0 ? "16px" : "0"
                    },
                    children: "Already on your list"
                }), He.map(a => {
                    const h = C.find(x => x.id === a.existing_id);
                    return s.jsxs("div", {
                        style: {
                            display: "flex",
                            alignItems: "center",
                            padding: "10px 0",
                            borderBottom: `1px solid ${V}`,
                            gap: "8px"
                        },
                        children: [s.jsxs("div", {
                            style: {
                                flex: 1
                            },
                            children: [s.jsxs("span", {
                                style: {
                                    fontFamily: k,
                                    fontSize: "16px",
                                    color: Q
                                },
                                children: [a.parsed.brand ? `${a.parsed.brand} ` : "", a.parsed.name]
                            }), s.jsxs("div", {
                                style: {
                                    fontFamily: k,
                                    fontSize: "13px",
                                    color: M,
                                    marginTop: "2px"
                                },
                                children: ["Currently: ×", (h == null ? void 0 : h.quantity) ?? 1]
                            })]
                        }), s.jsxs("button", {
                            onClick: async () => {
                                const x = (h == null ? void 0 : h.quantity) ?? 1
                                  , P = await fetch(`/api/list/${a.existing_id}`, {
                                    method: "PATCH",
                                    headers: {
                                        "Content-Type": "application/json"
                                    },
                                    body: JSON.stringify({
                                        quantity: x + (a.parsed.quantity || 1)
                                    })
                                });
                                if (P.ok) {
                                    const K = await P.json();
                                    j(re => vn(re.map(ot => ot.id === K.id ? K : ot)));
                                    const D = He.filter(re => re.existing_id !== a.existing_id);
                                    Gn(D),
                                    D.length === 0 && Ee.length === 0 && fn(!1)
                                }
                            }
                            ,
                            style: {
                                flexShrink: 0,
                                padding: "6px 14px",
                                borderRadius: "16px",
                                border: `1.5px solid ${O}`,
                                background: "none",
                                color: O,
                                fontFamily: k,
                                fontSize: "14px",
                                fontWeight: 600,
                                cursor: "pointer"
                            },
                            children: ["+", a.parsed.quantity || 1]
                        })]
                    }, a.existing_id)
                }
                )]
            }), Ee.length > 0 && s.jsx("button", {
                onClick: async () => {
                    for (const a of Ee)
                        await fetch(`/api/list/${a.id}`, {
                            method: "DELETE"
                        });
                    j(a => {
                        const h = new Set(Ee.map(x => x.id));
                        return a.filter(x => !h.has(x.id))
                    }
                    ),
                    xe([]),
                    He.length === 0 && fn(!1)
                }
                ,
                style: z.sheetDeleteBtn,
                children: "Undo all"
            }), s.jsx("button", {
                onClick: () => {
                    fn(!1),
                    xe([]),
                    Gn([])
                }
                ,
                style: z.sheetButton,
                children: "Done"
            })]
        }), Ud && s.jsxs(hl, {
            isOpen: !0,
            onClose: () => $r(!1),
            title: "Save List",
            children: [s.jsx("input", {
                type: "text",
                value: mn,
                onChange: a => Ur(a.target.value),
                onKeyDown: a => {
                    a.key === "Enter" && mn.trim() && cu()
                }
                ,
                placeholder: "List name (e.g. Weekly Groceries)",
                style: z.sheetTextInput,
                autoFocus: !0
            }), s.jsx("button", {
                onClick: cu,
                disabled: !mn.trim(),
                style: {
                    ...z.sheetButton,
                    opacity: mn.trim() ? 1 : .4
                },
                children: "Save"
            })]
        })]
    })
}
const ce = {
    container: {
        backgroundColor: Fe,
        fontFamily: k,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        paddingTop: "100px",
        paddingBottom: "40px",
        paddingLeft: "20px",
        paddingRight: "20px",
        minHeight: "100%",
        boxSizing: "border-box"
    },
    card: {
        width: "100%",
        maxWidth: "380px",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        textAlign: "center"
    },
    wordmark: {
        fontFamily: k,
        fontSize: "32px",
        fontWeight: 700,
        color: O,
        margin: "16px 0 0 0",
        letterSpacing: "-0.5px"
    },
    tagline: {
        fontFamily: k,
        fontSize: "15px",
        fontWeight: 400,
        color: M,
        margin: "8px 0 32px 0",
        lineHeight: "1.5",
        maxWidth: "280px"
    },
    inputGroup: {
        width: "100%",
        marginBottom: "16px"
    },
    label: {
        display: "block",
        fontFamily: k,
        fontSize: "13px",
        fontWeight: 500,
        color: M,
        marginBottom: "8px",
        textAlign: "left",
        textTransform: "uppercase",
        letterSpacing: "0.5px",
        paddingLeft: "16px"
    },
    phoneInput: {
        width: "100%",
        padding: "16px",
        fontSize: "20px",
        fontFamily: k,
        fontWeight: 500,
        color: Q,
        backgroundColor: X,
        border: `2px solid ${V}`,
        borderRadius: "12px",
        outline: "none",
        boxSizing: "border-box",
        textAlign: "left",
        letterSpacing: "0.5px",
        WebkitTextSizeAdjust: "100%"
    },
    button: {
        width: "100%",
        padding: "16px",
        fontSize: "16px",
        fontFamily: k,
        fontWeight: 600,
        color: X,
        backgroundColor: O,
        border: "none",
        borderRadius: "12px",
        cursor: "pointer",
        transition: "opacity 0.2s, transform 0.1s",
        WebkitTapHighlightColor: "transparent",
        letterSpacing: "0.3px"
    },
    error: {
        fontFamily: k,
        fontSize: "14px",
        color: nn,
        margin: "0 0 12px 0",
        fontWeight: 500
    },
    codePrompt: {
        fontFamily: k,
        fontSize: "15px",
        color: M,
        margin: "12px 0 4px 0"
    },
    phoneDisplay: {
        fontFamily: k,
        fontSize: "17px",
        fontWeight: 600,
        color: O,
        background: "none",
        border: "none",
        cursor: "pointer",
        padding: "4px 8px",
        borderRadius: "6px",
        marginBottom: "28px",
        textDecoration: "underline",
        textDecorationColor: `${O}40`,
        textUnderlineOffset: "3px",
        transition: "background-color 0.15s"
    },
    codeRow: {
        display: "flex",
        gap: "8px",
        marginBottom: "20px",
        width: "100%",
        justifyContent: "center"
    },
    codeBox: {
        width: "48px",
        height: "56px",
        fontSize: "24px",
        fontFamily: k,
        fontWeight: 600,
        color: Q,
        textAlign: "center",
        backgroundColor: X,
        border: `2px solid ${V}`,
        borderRadius: "10px",
        outline: "none",
        caretColor: O,
        transition: "border-color 0.15s",
        WebkitTextSizeAdjust: "100%"
    },
    verifying: {
        fontFamily: k,
        fontSize: "15px",
        color: O,
        fontWeight: 500,
        margin: "0 0 8px 0"
    }
}
  , z = {
    page: {
        height: "100svh",
        display: "flex",
        flexDirection: "column",
        backgroundColor: Fe,
        fontFamily: k,
        overflow: "hidden"
    },
    header: {
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "16px 20px",
        backgroundColor: X
    },
    headerWordmark: {
        fontFamily: k,
        fontSize: "22px",
        fontWeight: 700,
        color: O,
        letterSpacing: "-0.5px"
    },
    hamburgerBtn: {
        width: "40px",
        height: "40px",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "none",
        border: "none",
        cursor: "pointer",
        borderRadius: "8px",
        WebkitTapHighlightColor: "transparent"
    },
    menuOverlay: {
        position: "fixed",
        inset: 0,
        zIndex: 19
    },
    menuDropdown: {
        position: "absolute",
        top: "44px",
        right: 0,
        backgroundColor: X,
        borderRadius: "12px",
        boxShadow: "0 4px 20px rgba(0,0,0,0.15)",
        padding: "6px 0",
        minWidth: "180px",
        zIndex: 20
    },
    menuItem: e => ({
        display: "block",
        width: "100%",
        padding: "10px 18px",
        fontFamily: k,
        fontSize: "15px",
        fontWeight: e ? 600 : 400,
        color: e ? O : Q,
        background: "none",
        border: "none",
        textAlign: "left",
        cursor: "pointer",
        WebkitTapHighlightColor: "transparent"
    }),
    listArea: {
        flex: 1,
        overflowY: "auto",
        position: "relative"
    },
    emptyState: {
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        paddingTop: "80px",
        gap: "6px"
    },
    emptyText: {
        fontFamily: k,
        fontSize: "17px",
        fontWeight: 500,
        color: Q
    },
    emptySubtext: {
        fontFamily: k,
        fontSize: "15px",
        color: M
    },
    deptHeader: e => ({
        display: "flex",
        alignItems: "center",
        width: "100%",
        padding: "13px 20px",
        background: e ? `${O}0D` : "none",
        border: "none",
        borderBottom: `1px solid ${V}`,
        cursor: "pointer",
        textAlign: "left",
        WebkitTapHighlightColor: "transparent",
        gap: "8px",
        fontFamily: k,
        fontSize: "13px",
        fontWeight: 600,
        color: e ? O : M,
        textTransform: "uppercase",
        letterSpacing: "0.7px"
    }),
    deptCount: {
        fontSize: "12px",
        fontWeight: 500,
        color: M,
        marginLeft: "auto"
    },
    deptChevron: e => ({
        fontSize: "18px",
        color: M,
        transform: e ? "rotate(90deg)" : "none",
        transition: "transform 0.15s",
        lineHeight: 1,
        marginLeft: "4px"
    }),
    itemRow: {
        display: "flex",
        alignItems: "center",
        borderBottom: `1px solid ${V}`,
        backgroundColor: X
    },
    itemCheckBtn: {
        padding: "12px 10px 12px 20px",
        background: "none",
        border: "none",
        cursor: "pointer",
        flexShrink: 0,
        WebkitTapHighlightColor: "transparent",
        display: "flex",
        alignItems: "center"
    },
    itemCheck: e => ({
        width: "22px",
        height: "22px",
        borderRadius: "50%",
        border: `2px solid ${e ? O : V}`,
        backgroundColor: e ? O : "transparent",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        flexShrink: 0,
        fontSize: "12px",
        fontWeight: 700,
        color: X,
        transition: "all 0.15s"
    }),
    itemCenter: {
        flex: 1,
        padding: "12px 0",
        cursor: "pointer",
        display: "flex",
        flexDirection: "column",
        gap: "2px",
        WebkitTapHighlightColor: "transparent"
    },
    itemName: e => ({
        fontFamily: k,
        fontSize: "16px",
        color: e ? M : Q,
        textDecoration: e ? "line-through" : "none",
        transition: "all 0.15s"
    }),
    itemMeta: {
        fontFamily: k,
        fontSize: "13px",
        color: M
    },
    itemEditBtn: {
        padding: "8px 12px 8px 4px",
        background: "none",
        border: "none",
        cursor: "pointer",
        color: M,
        flexShrink: 0,
        WebkitTapHighlightColor: "transparent",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        width: "48px",
        height: "48px"
    },
    chatBar: {
        flexShrink: 0,
        display: "flex",
        alignItems: "center",
        gap: "8px",
        padding: "10px 12px",
        paddingBottom: "max(10px, env(safe-area-inset-bottom))",
        backgroundColor: X,
        borderTop: `1px solid ${V}`
    },
    chatIconBtn: {
        flexShrink: 0,
        width: "40px",
        height: "40px",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "none",
        border: "none",
        cursor: "pointer",
        borderRadius: "50%",
        WebkitTapHighlightColor: "transparent"
    },
    chatInput: {
        flex: 1,
        padding: "10px 14px",
        fontSize: "16px",
        fontFamily: k,
        color: Q,
        backgroundColor: Fe,
        border: `1.5px solid ${V}`,
        borderRadius: "20px",
        outline: "none",
        minWidth: 0
    },
    chatSendBtn: e => ({
        flexShrink: 0,
        width: "36px",
        height: "36px",
        borderRadius: "50%",
        backgroundColor: e ? O : V,
        color: e ? X : M,
        border: "none",
        cursor: e ? "pointer" : "default",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        transition: "background-color 0.15s",
        WebkitTapHighlightColor: "transparent"
    }),
    overlay: {
        position: "fixed",
        inset: 0,
        backgroundColor: "rgba(0,0,0,0.35)",
        display: "flex",
        alignItems: "flex-end",
        zIndex: 30
    },
    sheet: {
        width: "100%",
        backgroundColor: X,
        borderRadius: "20px 20px 0 0",
        padding: "24px 20px",
        paddingBottom: "max(32px, env(safe-area-inset-bottom))",
        display: "flex",
        flexDirection: "column",
        gap: "10px",
        maxHeight: "85dvh",
        overflowY: "auto"
    },
    sheetTitle: {
        fontFamily: k,
        fontSize: "18px",
        fontWeight: 600,
        color: Q
    },
    fieldLabel: {
        display: "block",
        fontFamily: k,
        fontSize: "12px",
        fontWeight: 600,
        color: M,
        textTransform: "uppercase",
        letterSpacing: "0.5px",
        marginBottom: "4px"
    },
    sheetRow: {
        display: "flex",
        alignItems: "center",
        gap: "12px"
    },
    sheetLabel: {
        fontFamily: k,
        fontSize: "14px",
        fontWeight: 500,
        color: M,
        flexShrink: 0,
        width: "36px"
    },
    sheetTextInput: {
        width: "100%",
        padding: "13px 16px",
        fontSize: "16px",
        fontFamily: k,
        color: Q,
        backgroundColor: Fe,
        border: `1.5px solid ${V}`,
        borderRadius: "12px",
        outline: "none",
        boxSizing: "border-box"
    },
    sheetSelect: {
        width: "100%",
        padding: "13px 16px",
        fontSize: "16px",
        fontFamily: k,
        color: Q,
        backgroundColor: Fe,
        border: `1.5px solid ${V}`,
        borderRadius: "12px",
        outline: "none",
        boxSizing: "border-box",
        appearance: "none",
        WebkitAppearance: "none",
        backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='8' viewBox='0 0 12 8'%3E%3Cpath d='M1 1l5 5 5-5' stroke='%236B6B6B' stroke-width='1.5' fill='none' stroke-linecap='round'/%3E%3C/svg%3E")`,
        backgroundRepeat: "no-repeat",
        backgroundPosition: "right 16px center",
        paddingRight: "40px"
    },
    qtyControl: {
        display: "flex",
        alignItems: "center",
        gap: "0",
        border: `1.5px solid ${V}`,
        borderRadius: "12px",
        overflow: "hidden",
        backgroundColor: Fe
    },
    qtyBtn: {
        width: "44px",
        height: "44px",
        border: "none",
        background: "none",
        fontSize: "20px",
        fontWeight: 400,
        color: O,
        cursor: "pointer",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        WebkitTapHighlightColor: "transparent"
    },
    qtyValue: {
        fontFamily: k,
        fontSize: "16px",
        fontWeight: 600,
        color: Q,
        minWidth: "32px",
        textAlign: "center"
    },
    sheetButton: {
        width: "100%",
        padding: "15px",
        fontSize: "16px",
        fontFamily: k,
        fontWeight: 600,
        color: X,
        backgroundColor: O,
        border: "none",
        borderRadius: "12px",
        cursor: "pointer"
    },
    sheetDeleteBtn: {
        width: "100%",
        padding: "13px",
        fontSize: "15px",
        fontFamily: k,
        fontWeight: 500,
        color: nn,
        backgroundColor: "transparent",
        border: `1px solid ${nn}40`,
        borderRadius: "12px",
        cursor: "pointer"
    }
}
  , Gh = `
  * { margin: 0; padding: 0; box-sizing: border-box; }

  html, body, #root {
    height: 100%;
  }

  body {
    background-color: ${Fe};
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
  }

  input:focus {
    border-color: ${O} !important;
    box-shadow: 0 0 0 3px ${O}18;
  }

  button:active {
    transform: scale(0.98);
  }

  /* Hide number input spinners */
  input::-webkit-outer-spin-button,
  input::-webkit-inner-spin-button {
    -webkit-appearance: none;
    margin: 0;
  }

  /* Selection color */
  ::selection {
    background-color: ${O}30;
  }

  /* Penny loading pulse */
  @keyframes penny-pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.2; }
  }
  .penny-pulse {
    animation: penny-pulse 1.2s ease-in-out infinite;
  }
`
  , Ad = document.createElement("style");
Ad.textContent = Gh;
document.head.appendChild(Ad);
oi.createRoot(document.getElementById("root")).render(s.jsx(Ff.StrictMode, {
    children: s.jsx(Xh, {})
}));
