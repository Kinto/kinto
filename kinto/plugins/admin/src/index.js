import React from "react";
import ReactDOM from "react-dom";
import KintoAdmin from "kinto-admin";
import * as signoffPlugin from "kinto-admin/lib/plugins/signoff";

/* Make sure we remove previously saved passwords */
localStorage.removeItem('kinto-admin-session');

const settings = {
  maxPerPage: 50,
  singleServer: document.location.toString().split('/admin/')[0],
  ...window.globalSettings,
};


ReactDOM.render(
  <KintoAdmin settings={settings} plugins={[signoffPlugin]}/>,
  document.getElementById("root")
);
