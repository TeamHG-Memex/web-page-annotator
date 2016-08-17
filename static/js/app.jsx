var App = React.createClass({
    getInitialState: function () {
        return {
            idx: 0,
            labelAt: null,
            labeled: {}  // url -> selector -> labelData
        };
    },
    render: function () {
        console.log('App.render', this.state);
        var labelDropdown;
        if (this.state.labelAt) {
            labelDropdown = <LabelDropdown
                labels={ this.props.labels }
                position={ this.state.labelAt }
                onLabelSelected={ this.onLabelSelected }
                />
        }
        var url = this.currentUrl();
        var btnClasses = 'waves-effect waves-light btn';
        var labeled = this.state.labeled[url];
        return <div>
            <div id="controls">
                <a className={ btnClasses } onClick={ this.onReload }>reload</a>{' '}
                <a className={ btnClasses + (this.previousEnabled() ? '' : ' disabled') }
                   onClick={ this.onPrevious }>
                    <i className="material-icons left">skip_previous</i>prev
                </a>{' '}
                <div className="chip url-chip">{ url || '-' }</div>{' '}
                <a className={ btnClasses + (this.nextEnabled() ? '' : ' disabled') }
                   onClick={ this.onNext }>
                    <i className="material-icons right">skip_next</i>next
                </a>{' '}
                <a className={ btnClasses + ' disabled' }>import urls</a>{' '}
                <a className={ btnClasses + ' disabled' }>export pages & labels</a>{' '}
            </div>
            <IFrame url={ url } labeled={ labeled }/>
            { labelDropdown }
        </div>;
    },
    currentUrl: function () {
        return this.props.urls[this.state.idx];
    },
    onPrevious: function (event) {
        if (this.previousEnabled()) {
            var state = Object.assign({}, this.state);
            state.idx -= 1;
            this.setState(state);
        }
        event.preventDefault();
    },
    onNext: function (event) {
        if (this.nextEnabled()) {
            var state = Object.assign({}, this.state);
            state.idx += 1;
            this.setState(state);
        }
        event.preventDefault();
    },
    onReload: function () {
        window.alert('TODO');
    },
    previousEnabled: function () {
        return this.state.idx > 0;
    },
    nextEnabled: function () {
        return this.state.idx < (this.props.urls.length - 1);
    },
    onLabelElement: function (event) {
        var data = event.data;
        console.log('onLabelElement', data);
        this.setState(Object.assign({}, this.state, {labelAt: data}));
    },
    onLabelSelected: function (text) {
        var labelData = {text: text, selector: this.state.labelAt.selector};
        // notifyChildOfLabel(labelData);
        var url = this.currentUrl();
        var labeled = Object.assign({}, this.state.labeled);
        labeled[url] = Object.assign({}, labeled[url] || {});
        labeled[url][labelData.selector] = labelData;
        this.setState({labeled: labeled, labelAt: null});
    },
    onCloseLabels: function () {
        this.setState(Object.assign({}, this.state, {labelAt: null}));
    },
    componentDidMount: function () {
        document.body.addEventListener('label-element', this.onLabelElement);
        document.body.addEventListener('close-labels', this.onCloseLabels);
    },
    componentWillUnmount: function () {
        document.body.removeEventListener('label-element', this.onLabelElement);
        document.body.removeEventListener('close-labels', this.onCloseLabels);
    }
});

function notifyChildOfLabel(labelData) {
    var eventToChild = document.createEvent('Event');
    eventToChild.initEvent('label-selected', true, true);
    eventToChild.data = labelData;
    document.getElementById('child-page').contentWindow
        .document.body.dispatchEvent(eventToChild);
}

var IFrame = React.createClass({
    render: function () {
        // TODO (later): handle resize
        return <iframe id="child-page"
                       src={ '/' + this.props.url }
                       ref={ this.ref.bind(this) }
                       >
        </iframe>;
    },
    ref: function (iframe) {
        if (iframe) {
            var iframeRect = iframe.getBoundingClientRect();
            iframe.style.height = (window.innerHeight - iframeRect.top) + 'px';
            iframe.style.width = window.innerWidth + 'px';
            var labeled = this.props.labeled;
            if (labeled) {
                Object.keys(labeled).forEach(function (selector) {
                    notifyChildOfLabel(labeled[selector]);
                });
            }
        }
    }
});

var LabelDropdown = React.createClass({
    render: function () {
        var labels = this.props.labels.map(function (text) {
            return <Label text={ text } onLabelSelected={ this.props.onLabelSelected }/>;
        }.bind(this));
        var position = this.props.position;
        return <div
            ref={function (div) {
                if (div) {
                    div.style.left = position.x + 'px';
                    div.style.top = position.y + 'px';
                }
            }}
            className="collection label-dropdown">
            { labels }</div>;
    }
});

var Label = React.createClass({
    render: function () {
        return <a href="#!" className="collection-item" onClick={ this.onClick }>
            { this.props.text }</a>;
    },
    onClick: function (event) {
        this.props.onLabelSelected(this.props.text);
        event.preventDefault();
    }
});

var labels = ['Title', 'Body', 'Author', 'Date'];
var urls = ['http://risk.ru', 'http://twitter.com', 'http://google.com'];

ReactDOM.render(
    <App urls={ urls } labels={ labels }/>,
    document.getElementById('app')
);
