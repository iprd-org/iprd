---
layout: default
title: Radio Data Files
nav_order: 4
---

# Radio Data Files

This page provides access to the data files that power the International Public Radio Directory (IPRD). These files are available in various formats and organized by countries and broadcasting groups.

## Complete Collection

- [All Stations (M3U)]({{ site.baseurl }}/site_data/all_stations.m3u) - Complete playlist of all radio stations in the directory
- [Summary (JSON)]({{ site.baseurl }}/site_data/summary.json) - Summary information about the directory in JSON format

## Country-Specific Playlists

Browse radio stations by country code. Each file contains all stations from the specified country in M3U format.

{% assign countries = "ad,ae,af,ag,ai,al,am,ao,ar,as,at,au,aw,ax,az,ba,bb,bd,be,bf,bg,bh,bi,bj,bm,bn,bo,bq,br,bs,bt,bw,by,bz,ca,cd,cf,cg,ch,ci,ck,cl,cm,cn,co,cr,cu,cv,cw,cy,cz,de,dk,dm,do,dz,ec,ee,eg,es,et,fi,fj,fk,fm,fo,fr,ga,gb,gd,ge,gf,gg,gh,gi,gl,gm,gn,gp,gq,gr,gt,gu,gy,hk,hn,hr,ht,hu,id,ie,il,im,in,io,iq,ir,is,it,je,jm,jo,jp,ke,kg,kh,km,kn,kp,kr,kw,ky,kz,la,lb,lc,li,lk,lr,ls,lt,lu,lv,ly,ma,mc,md,me,mg,mh,mk,ml,mm,mn,mo,mq,mr,ms,mt,mu,mw,mx,my,mz,na,nc,ng,ni,nl,no,np,nr,nz,om,pa,pe,pf,pg,ph,pk,pl,pm,pr,ps,pt,py,qa,re,ro,rs,ru,rw,sa,sc,sd,se,sg,sh,si,sk,sl,sm,sn,so,sr,ss,sv,sy,sz,tc,tf,tg,th,tj,tl,tm,tn,to,tr,tt,tw,tz,ua,ug,um,us,uy,uz,va,vc,ve,vg,vi,vn,vu,wf,xk,ye,yt,za,zm,zw" | split: "," %}

<div class="country-grid">
{% for country in countries %}
  <div class="country-item">
    <a href="{{ site.baseurl }}/site_data/by_country/{{ country }}.m3u">{{ country | upcase }}</a>
  </div>
{% endfor %}
</div>

<style>
.country-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(60px, 1fr));
  gap: 10px;
  margin: 20px 0;
}
.country-item {
  background-color: #2c3038;
  text-align: center;
  padding: 8px;
  border-radius: 4px;
}
.country-item a {
  color: #fff;
  text-decoration: none;
}
.country-item:hover {
  background-color: #3f444e;
}
</style>

## Using These Files

These M3U playlist files can be used with most media players:

1. Download the desired playlist file
2. Open it with your preferred media player (VLC, Winamp, iTunes, etc.)
3. Select the station you want to listen to

For more information on using these files, please check our [Usage Guide](./usage.md).