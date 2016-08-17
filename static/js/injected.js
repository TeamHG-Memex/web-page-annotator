document.addEventListener('DOMContentLoaded', function() {
    // TODO - do we need to remove listeners in beforeunload event?

    document.body.addEventListener('contextmenu', function (event) {
        var eventToParent = document.createEvent('Event');
        eventToParent.initEvent('label-element', true, true);
        eventToParent.data = {
            x: event.clientX,
            y: event.clientY,
            selector: elementSelector(eventTarget(event))
        };
        window.parent.document.body.dispatchEvent(eventToParent);
        event.preventDefault();
    });

    // TODO - same for Esc
    document.body.addEventListener('click', function (event) {
        var eventToParent = document.createEvent('Event');
        eventToParent.initEvent('close-labels', true, true);
        window.parent.document.body.dispatchEvent(eventToParent);
    });

    document.body.addEventListener('label-selected', function (event) {
        var labelData = event.data;
        var el = document.querySelector(labelData.selector);
        // TODO - different colors for different labels, or add text? Or both
        if (labelData.text) {
            el.classList.add('web-page-annotator-selected');
        } else {
            el.classList.remove('web-page-annotator-selected');
        }
    });

    // TODO - remove highligh when leaving window
    var prevHlElement = null;
    var hlClass = 'web-page-annotator-highlight';
    document.addEventListener('mousemove', function(event) {
        var elem = eventTarget(event);
        if (prevHlElement != null) {
            prevHlElement.classList.remove(hlClass);
        }
        elem.classList.add(hlClass);
        prevHlElement = elem;
    }, true);

    function eventTarget(event) {
        return event.target || event.srcElement;
    }

    function elementSelector(el) {
        var names = [];
        while (el.parentNode) {
            if (el.id) {
                names.unshift('#' + el.id);
                break;
            } else {
                if (el == el.ownerDocument.documentElement) {
                    names.unshift(el.tagName);
                } else {
                    for (var c = 1, e = el; e.previousElementSibling; c++) {
                        e = e.previousElementSibling;
                    }
                    names.unshift(el.tagName + ':nth-child(' + c + ')');
                }
                el = el.parentNode;
            }
        }
        return names.join(' > ');
    }

});