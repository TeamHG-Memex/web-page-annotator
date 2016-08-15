$(document).ready(function () {
    console.log('hi from parent');
    $(document.body).on('label-element', function (event) {
        console.log('event in parent', event);
    });
});