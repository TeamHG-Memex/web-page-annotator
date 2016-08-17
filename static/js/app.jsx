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
        var url = this.currentUrl();
        var labelDropdown;
        if (this.state.labelAt) {
            var urlLabeled = this.state.labeled[url];
            var labelValue;
            if (urlLabeled) {
                labelValue = urlLabeled[this.state.labelAt.selector];
            }
            labelDropdown = <LabelDropdown
                labels={ this.props.labels }
                position={ this.state.labelAt }
                value={ labelValue }
                onLabelFinishEdit={ this.onLabelFinishEdit }
                />
        }
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
            this.setState({idx: this.state.idx - 1});
        }
        event.preventDefault();
    },
    onNext: function (event) {
        if (this.nextEnabled()) {
            this.setState({idx: this.state.idx + 1});
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
    onLabelStartEdit: function (event) {
        this.setState({labelAt: event.data});
    },
    onLabelFinishEdit: function (text, wasSelected) {
        var labelData = {selector: this.state.labelAt.selector};
        if (!wasSelected) {
            labelData.text = text;
        }
        var url = this.currentUrl();
        var labeled = Object.assign({}, this.state.labeled);
        labeled[url] = Object.assign({}, labeled[url] || {});
        labeled[url][labelData.selector] = labelData;
        this.setState({labeled: labeled, labelAt: null});
    },
    onLabelDiscardEdit: function () {
        this.setState({labelAt: null});
    },
    componentDidMount: function () {
        document.body.addEventListener('labelStartEdit', this.onLabelStartEdit);
        document.body.addEventListener('labelDiscardEdit', this.onLabelDiscardEdit);
    },
    componentWillUnmount: function () {
        document.body.removeEventListener('labelStartEdit', this.onLabelStartEdit);
        document.body.removeEventListener('labelDiscardEdit', this.onLabelDiscardEdit);
    }
});

function notifyChildOfLabel(labelData, iframe) {
    var eventToChild = document.createEvent('Event');
    eventToChild.initEvent('labelFinishEdit', true, true);
    eventToChild.data = labelData;
    iframe = iframe || document.getElementById('child-page');
    iframe.contentDocument.body.dispatchEvent(eventToChild);
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
                var notifyChild = function () {
                    Object.keys(labeled).forEach(function (selector) {
                        notifyChildOfLabel(labeled[selector], iframe);
                    });
                };
                if (iframe.contentWindow.location.pathname != '/' + this.props.url) {
                    // FIXME - this is a gross hack. At least, we should determine
                    // when the child iframe has switched location and loaded DOM
                    window.setTimeout(notifyChild, 1000);
                } else {
                    notifyChild();
                }
            }
        }
    }
});

var LabelDropdown = React.createClass({
    render: function () {
        var labels = this.props.labels.map(function (text) {
            return <Label
                text={ text }
                selected={ this.props.value && text === this.props.value.text }
                onLabelFinishEdit={ this.props.onLabelFinishEdit }/>;
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
        var text = this.props.text;
        if (this.props.selected) {
            text = <span className="selected-label">{ text }</span>;
        }
        return <a href="#!" className="collection-item" onClick={ this.onClick }>
            { text }</a>;
    },
    onClick: function (event) {
        this.props.onLabelFinishEdit(this.props.text, this.props.selected);
        event.preventDefault();
    }
});

var labels = ['Title', 'Body', 'Author', 'Date'];
var urls = ['http://risk.ru', 'http://google.com', 'http://twitter.com'];

ReactDOM.render(
    <App urls={ urls } labels={ labels }/>,
    document.getElementById('app')
);
