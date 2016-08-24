var App = React.createClass({
    getInitialState: function () {
        return {
            workspaces: [],
            activeWorkspace: null,
        };
    },
    componentDidMount: function () {
        $.ajax({
            url: URLS.ws_list,
            dataType: 'json',
            success: function (data) {
                this.setState(data);
            }.bind(this)
        });
    },
    render: function () {
        if (this.state.activeWorkspace) {
            var ws = this.state.activeWorkspace;
            return <Workspace
                id={ ws.id }
                name={ ws.name }
                onClose={ this.onCloseWorkspace }
            />;
        } else {
            return <WorkspaceList
                workspaces={ this.state.workspaces }
                onWorkspaceSelected={ this.onWorkspaceSelected }
                onAddWorkspace={ this.onAddWorkspace }
            />;
        }
    },
    onAddWorkspace: function () {
        this.setState({activeWorkspace: {}});
    },
    onWorkspaceSelected: function (ws) {
        this.setState({activeWorkspace: ws});
    },
    onCloseWorkspace: function (ws) {
        var found = false;
        var workspaces = this.state.workspaces.map(function (_ws) {
            if (_ws.id === ws.id) {
                found = true;
                return ws;
            } else {
                return _ws;
            }
        });
        if (!found) {
            workspaces.push(ws);
        }
        this.setState({activeWorkspace: null, workspaces: workspaces});
    }
});

var WorkspaceList = React.createClass({
    render: function () {
        var workspaces = this.props.workspaces.map(function (ws) {
            return <WorkspaceInline
                ws={ ws }
                onWorkspaceSelected={ this.props.onWorkspaceSelected }
            />;
        }.bind(this));
        return <div className="container">
            <h2>Web Page Annotator</h2>
            <h4>Workspaces</h4>
            <div className="collection">{ workspaces }</div>
            <a className="waves-effect waves-light btn"
               onClick={ this.onAddWorkspace }>add workspace</a>
            </div>;
    },
    onAddWorkspace: function (event) {
        event.preventDefault();
        this.props.onAddWorkspace();
    }
});


var WorkspaceInline = React.createClass({
    render: function () {
        return <a
            href="#!"
            onClick={ this.onClick }
            className="collection-item">{ this.props.ws.name || 'Untitled' }</a>;
    },
    onClick: function (event) {
        event.preventDefault();
        this.props.onWorkspaceSelected(this.props.ws);
    }
});

var Workspace = React.createClass({
    getInitialState: function () {
        return {
            id: this.props.id,
            name: this.props.name,
            labels: [],
            urls: [],
            labeled: {},  // url -> selector -> labelData
            urlIdx: 0,
            editingWorkspace: !this.props.id,
            editingLabelAt: null
        };
    },
    componentDidMount: function () {
        document.body.addEventListener('labelStartEdit', this.onLabelStartEdit);
        document.body.addEventListener('labelDiscardEdit', this.onLabelDiscardEdit);
        if (this.state.id) {
            $.ajax({
                url: URLS.ws_list + this.state.id + '/',
                dataType: 'json',
                success: function (data) {
                    this.setState(data);
                }.bind(this)
            });
        }
    },
    componentWillUnmount: function () {
        document.body.removeEventListener('labelStartEdit', this.onLabelStartEdit);
        document.body.removeEventListener('labelDiscardEdit', this.onLabelDiscardEdit);
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
            iframe = <IFrame wsId={ this.state.id } url={ url } labeled={ labeled }/>
        }
        if (this.state.editingWorkspace) {
            workspaceSettings = <WorkspaceSettings
                id={ this.state.id }
                name={ this.state.name }
                urls={ this.state.urls }
                labels={ this.state.labels }
                onWorkspaceDiscardEdit={ this.onWorkspaceDiscardEdit }
                onWorkspaceFinishEdit={ this.onWorkspaceFinishEdit }
                />;
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
                <div className="chip url-chip" onClick={ this.onUrlChipClick }>
                    { url || '-' }</div>{' '}
                <a className={ btnClasses(this.nextEnabled()) }
                   onClick={ this.onNext }>
                    <i className="material-icons right">skip_next</i>next
                </a>{' '}
                <a className={ btnClasses(true) }
                   onClick={ this.onWorkspaceStartEdit }>workspace</a>{' '}
                <a className={ btnClasses(this.exportEnabled()) }
                   href={ this.exportURL() }>export</a>{' '}
                <a className={ btnClasses(true) }
                   onClick={ this.onClose }>close</a>{' '}
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
    onClose: function (event) {
        this.props.onClose({id: this.state.id, name: this.state.name});
    },
    onUrlChipClick: function (event) {
        event.preventDefault();
        selectText(event.target);
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
        return Boolean(this.state.id && this.currentUrl());
    },
    exportURL: function () {
        if (this.state.id) {
            return URLS.ws_export + this.state.id + '/';
        } else {
            return '#!';
        }
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
        $.ajax({
            url: URLS.label,
            method: 'POST',
            dataType: 'json',
            data: JSON.stringify({
                wsId: this.state.id,
                url: url,
                selector: labelData.selector,
                label: labelData.text
            })
        });
    },
    onLabelDiscardEdit: function () {
        this.setState({editingLabelAt: null});
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
                       src={ this.proxyUrl() }
                       ref={ this.ref.bind(this) }
                       >
        </iframe>;
    },
    proxyUrl: function () {
        return URLS.proxy + this.props.wsId +
            '/?url=' + window.encodeURIComponent(this.props.url);
    },
    ref: function (iframe) {
        if (iframe) {
            var iframeRect = iframe.getBoundingClientRect();
            iframe.style.height = (window.innerHeight - iframeRect.top) + 'px';
            iframe.style.width = window.innerWidth + 'px';
            var labeled = this.props.labeled;
            if (labeled) {
                var notifyChild = function () {
                    var iframeLoc = iframe.contentWindow.location;
                    if ((iframeLoc.pathname + iframeLoc.search) === this.proxyUrl() &&
                            iframe.contentDocument.readyState === 'complete') {
                        Object.keys(labeled).forEach(function (selector) {
                            notifyChildOfLabel(labeled[selector], iframe);
                        });
                    } else {
                        // We could do the readyState check with an event instead of
                        // a busy wait, but I don't know how to do it with location check.
                        window.setTimeout(notifyChild, 50);
                    }
                }.bind(this);
                notifyChild();
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
            id: this.props.id,
            name: this.props.name,
            urls_text: this.props.urls.join('\n'),
            labels_text: this.props.labels.join('\n'),
            saving: false
        };
    },
    render: function () {
        var btnClass = 'waves-effect waves-light btn-flat';
        if (this.state.saving) {
            btnClass += ' disabled';
        }
        return <div id="workspace-settings" className="modal modal-fixed-footer">
                <div className="modal-content">
                    <h4>Workspace setup</h4>
                    <input
                        type="text"
                        placeholder="Workspace name"
                        onChange={ this.updateName }
                        value={ this.state.name || '' }/>
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
                    <a className={ btnClass }
                       onClick={ this.onOk }>ok</a>{ ' ' }
                    <a className={ btnClass }
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
    onOk: function (event) {
        event.preventDefault();
        var ws = {
            id: this.state.id,
            name: this.state.name,
            urls: this.state.urls_text.trim().split('\n'),
            labels: this.state.labels_text.trim().split('\n')
        };
        this.setState({saving: true});
        $.ajax({
            url: URLS.ws_list,
            dataType: 'json',
            type: 'POST',
            data: JSON.stringify(ws),
            success: function (data) {
                ws.id = data.id;
                this.setState({saving: false});
                this.props.onWorkspaceFinishEdit(ws);
            }.bind(this),
            error: function(xhr, status, err) {
                this.setState({saving: false});
                // TODO
                console.error(this.props.url, status, err.toString());
            }.bind(this)
        });
    },
    onCancel: function (event) {
        event.preventDefault();
        this.props.onWorkspaceDiscardEdit();
    }
});


function selectText(element) {
    var range, selection;
    if (document.body.createTextRange) {
        range = document.body.createTextRange();
        range.moveToElementText(element);
        range.select();
    } else if (window.getSelection) {
        selection = window.getSelection();
        range = document.createRange();
        range.selectNodeContents(element);
        selection.removeAllRanges();
        selection.addRange(range);
    }
}

ReactDOM.render(<App/>, document.getElementById('app'));
