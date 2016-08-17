var Workspace = React.createClass({
    getInitialState: function () {
        return {
            name: '',
            labels: [],
            urls: [],
            urlIdx: 0,
            editingWorkspace: false,
            editingLabelAt: null,
            labeled: {}  // url -> selector -> labelData
        };
    },
    render: function () {
        var url = this.currentUrl();
        var labelDropdown, iframe, workspaceSettings;
        if (url) {
            if (this.state.editingLabelAt) {
                var urlLabeled = this.state.labeled[url];
                var labelValue;
                if (urlLabeled) {
                    labelValue = urlLabeled[this.state.editingLabelAt.selector];
                }
                labelDropdown = <LabelDropdown
                    labels={ this.state.labels }
                    position={ this.state.editingLabelAt }
                    value={ labelValue }
                    onLabelFinishEdit={ this.onLabelFinishEdit }
                />
            }
            var labeled = this.state.labeled[url];
            iframe = <IFrame url={ url } labeled={ labeled }/>
        }
        if (this.state.editingWorkspace) {
            workspaceSettings = <WorkspaceSettings
                name={ this.state.name }
                urls={ this.state.urls }
                labels={ this.state.labels }
                onWorkspaceDiscardEdit={ this.onWorkspaceDiscardEdit }
                onWorkspaceFinishEdit={ this.onWorkspaceFinishEdit }/>;
        }
        var btnClasses = function (enabled) {
            return 'waves-effect waves-light btn' + (enabled ? '' : ' disabled');
        };
        return <div>
            <div id="controls">
                <a className={ btnClasses(this.reloadEnabled()) }
                   onClick={ this.onReload }>reload</a>{' '}
                <a className={ btnClasses(this.previousEnabled()) }
                   onClick={ this.onPrevious }>
                    <i className="material-icons left">skip_previous</i>prev
                </a>{' '}
                <div className="chip url-chip">{ url || '-' }</div>{' '}
                <a className={ btnClasses(this.nextEnabled()) }
                   onClick={ this.onNext }>
                    <i className="material-icons right">skip_next</i>next
                </a>{' '}
                <a className={ btnClasses(true) }
                    onClick={ this.onWorkspaceStartEdit }>workspace</a>{' '}
                <a className={ btnClasses(this.exportEnabled()) }>export pages & labels</a>{' '}
            </div>
            { iframe }
            { labelDropdown }
            { workspaceSettings }
        </div>;
    },
    currentUrl: function () {
        if (this.state.urls.length > 0) {
            return this.state.urls[this.state.urlIdx];
        }
    },
    onPrevious: function (event) {
        if (this.previousEnabled()) {
            this.setState({urlIdx: this.state.urlIdx - 1});
        }
        event.preventDefault();
    },
    onNext: function (event) {
        if (this.nextEnabled()) {
            this.setState({urlIdx: this.state.urlIdx + 1});
        }
        event.preventDefault();
    },
    onReload: function () {
        window.alert('TODO');
    },
    onWorkspaceStartEdit: function () {
        this.setState({editingWorkspace: true});
    },
    onWorkspaceFinishEdit: function (updated) {
        if (this.state.urlIdx >= updated.urls.length) {
            updated.urlIdx = 0;
        }
        updated.editingWorkspace = false;
        this.setState(updated);
    },
    onWorkspaceDiscardEdit: function () {
        this.setState({editingWorkspace: false});
    },
    previousEnabled: function () {
        return this.state.urlIdx > 0;
    },
    nextEnabled: function () {
        return this.state.urlIdx < (this.state.urls.length - 1);
    },
    reloadEnabled: function () {
        return Boolean(this.currentUrl());
    },
    exportEnabled: function () {
        return Boolean(this.currentUrl());
    },
    onLabelStartEdit: function (event) {
        this.setState({editingLabelAt: event.data});
    },
    onLabelFinishEdit: function (text, wasSelected) {
        var labelData = {selector: this.state.editingLabelAt.selector};
        if (!wasSelected) {
            labelData.text = text;
        }
        var url = this.currentUrl();
        var labeled = Object.assign({}, this.state.labeled);
        labeled[url] = Object.assign({}, labeled[url] || {});
        labeled[url][labelData.selector] = labelData;
        this.setState({labeled: labeled, editingLabelAt: null});
    },
    onLabelDiscardEdit: function () {
        this.setState({editingLabelAt: null});
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

var WorkspaceSettings = React.createClass({
    getInitialState: function () {
        return {
            name: this.props.name,
            urls_text: this.props.urls.join('\n'),
            labels_text: this.props.labels.join('\n')
        };
    },
    render: function () {
        return <div id="workspace-settings" className="modal modal-fixed-footer">
                <div className="modal-content">
                    <h4>Workspace setup</h4>
                    <input
                        type="text"
                        placeholder="Workspace name"
                        onChange={ this.updateName }
                        value={ this.state.name }/>
                    <textarea
                        className="materialize-textarea"
                        onChange={ this.updateLabels }>
                        { this.state.labels_text }</textarea>
                    <label>Labeles (one on a line)</label>
                    <textarea
                        className="materialize-textarea"
                        onChange={ this.updateUrls }>
                        { this.state.urls_text }</textarea>
                    <label>Urls (one on a line)</label>
                </div>
                <div className="modal-footer">
                    <a className="waves-effect waves-light btn-flat"
                       onClick={ this.onImport }>ok</a>{ ' ' }
                    <a className="waves-effect waves-light btn-flat"
                       onClick={ this.onCancel }>cancel</a>{ ' ' }
                </div>
            </div>;
    },
    updateUrls: function (event) {
        this.setState({urls_text: event.target.value});
    },
    updateLabels: function (event) {
        this.setState({labels_text: event.target.value});
    },
    updateName: function (event) {
        this.setState({name: event.target.value});
    },
    onImport: function (event) {
        event.preventDefault();
        this.props.onWorkspaceFinishEdit({
            name: this.state.name,
            urls: this.state.urls_text.split('\n'),
            labels: this.state.labels_text.split('\n')
        });
    },
    onCancel: function (event) {
        event.preventDefault();
        this.props.onWorkspaceDiscardEdit();
    }
});

// var labels = ['Title', 'Body', 'Author', 'Date'];
// var urls = ['http://risk.ru', 'http://google.com', 'http://twitter.com'];

ReactDOM.render(
    <Workspace/>,
    document.getElementById('app')
);
