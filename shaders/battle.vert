#version 450 core
layout(location=0) in vec4 entity;
layout(location=1) in vec4 roles;
layout(location=2) in vec4 metadata;
layout(location=3) in vec4 lifecycle; // projectile generation/active/source-generation/reserved @48
uniform vec3 camera;
uniform vec4 weather;
out vec3 worldPosition;
flat out int materialMode;
uniform vec2 angle;
uniform int terrain;
uniform int tactical;
uniform vec2 selectedGoal;
uniform vec4 playerHealth; // health, suppression, redeploy progress, damage flash
uniform int localPlayer;
uniform vec4 vehicleState; // aboard,cannon ammo,cooldown,entity index+1
uniform vec3 operationInfo; // req/1000, supply/1200, operation state
uniform vec4 weaponState; // rounds, reload remaining fraction, hit flash, muzzle flash
out vec3 colour;
out float effectAlpha;
out vec2 effectUV;
flat out int effectType;
out float distanceFog;
const vec3 corners[8]=vec3[8](vec3(-1,0,-1),vec3(1,0,-1),vec3(1,2,-1),vec3(-1,2,-1),vec3(-1,0,1),vec3(1,0,1),vec3(1,2,1),vec3(-1,2,1));
const int faces[36]=int[36](0,2,1,0,3,2,4,5,6,4,6,7,0,1,5,0,5,4,3,7,6,3,6,2,0,4,7,0,7,3,1,2,6,1,6,5);
float height(vec2 p){vec2 q=p-vec2(4000);return 12+q.x*q.x*.000001+q.y*q.y*.0000005+max(0.,1.-abs(q.x)/800.)*18.;}
void main(){
 effectAlpha=1.;effectUV=vec2(0);effectType=0;worldPosition=vec3(0);materialMode=terrain;
 if(terrain==9){const vec2 sky[3]=vec2[3](vec2(-1,-1),vec2(3,-1),vec2(-1,3));effectUV=sky[gl_VertexID];gl_Position=vec4(effectUV,.99999,1);colour=vec3(1);distanceFog=0;return;}
 if(terrain==4){int v=gl_VertexID%6,bar=gl_VertexID/6;vec2 c=vec2((v==1||v==2||v==4)?1:-1,(v==2||v==4||v==5)?1:-1);vec2 size=bar==0?vec2(.015,.002):vec2(.0012,.026); gl_Position=vec4((selectedGoal-vec2(4000))/4300+c*size,0,1);colour=vec3(.65,1,.45);distanceFog=0;return;}
 if(terrain==2){
  int v=gl_VertexID%6,bar=gl_VertexID/6;
  vec2 c=vec2((v==1||v==2||v==4)?1:-1,(v==2||v==4||v==5)?1:-1);
  vec2 centre=vec2(0),size=bar==0?vec2(.009,.0015):vec2(.0009,.016);
  colour=mix(vec3(.9,.95,.86),vec3(.2,1,.3),weaponState.z);
  if(bar>=2&&bar<32){centre=vec2(.48+float(bar-2)*.013,-.90);size=vec2(.004,.026);colour=float(bar-2)<weaponState.x?vec3(.75,.83,.57):vec3(.18,.22,.19);}
  if(bar==32){centre=vec2(.675,-.83);size=vec2(.19*(1-weaponState.y),.008);colour=weaponState.y>0?vec3(.95,.68,.16):vec3(.17,.20,.17);}
  if(bar==33){centre=vec2(0,-.025);size=vec2(.013,.002);colour=vec3(.1,.9,.25)*weaponState.z; if(weaponState.z<=0)size=vec2(0);}
  if(bar==34){centre=vec2(.26,-.86);size=vec2(.075,.15);colour=vec3(.12,.15,.16);}
  if(bar==35){centre=vec2(.17,-.68);size=vec2(.02,.12);colour=mix(vec3(.08,.10,.11),vec3(.8,.48,.16),weaponState.w*.35);}
  if(bar==36){centre=vec2(-.73,.90);size=vec2(.20*clamp(operationInfo.x,0,1),.009);colour=vec3(.83,.68,.25);}
  if(bar==37){centre=vec2(-.73,.85);size=vec2(.20*clamp(operationInfo.y,0,1),.009);colour=vec3(.22,.62,.75);}
  if(bar==38){centre=vec2(0,.97);size=vec2(.95,.014);colour=operationInfo.z==1?vec3(.16,.8,.25):(operationInfo.z==2?vec3(.9,.12,.1):(operationInfo.z==3?vec3(.95,.65,.08):vec3(.13,.25,.32)));}
  if(bar==39){centre=vec2(-.68,-.9);size=vec2(.24*playerHealth.x,.016);colour=mix(vec3(.9,.13,.1),vec3(.15,.8,.3),playerHealth.x);}
  if(bar==40){centre=vec2(-.68,-.85);size=vec2(.24*clamp(playerHealth.y,0,1),.007);colour=vec3(.9,.57,.16);}
  if(bar==41){centre=vec2(0,.78);size=vec2(.25*playerHealth.z,.015);colour=vec3(.9,.22,.16);if(playerHealth.x>0)size=vec2(0);}
  if(bar==42){centre=vec2(0,-.97);size=vec2(.98,.018);colour=vec3(.9,.1,.08)*playerHealth.w;if(playerHealth.w<=0)size=vec2(0);}
  if(bar==43){centre=vec2(.65,-.77);size=vec2(.18*clamp(vehicleState.y/20.,0,1),.012);colour=vec3(1.,.66,.2);if(vehicleState.x<=0)size=vec2(0);}
  if(vehicleState.x>0){if(bar==34||bar==35)size=vec2(0);if(bar<2)colour=vec3(1.,.75,.3);}
  if(bar==34||bar==35)size=vec2(0); // first-person weapon is an actual source mesh
  if((tactical!=0||playerHealth.x<=0)&&(bar<2||bar==34||bar==35))size=vec2(0);
  gl_Position=vec4(centre+c*size,0,1);distanceFog=0;return;
 }
 vec3 world;
 if(terrain==10){int drop=gl_VertexID/6,v=gl_VertexID%6;float seed=float(drop);vec3 centre=camera+vec3(fract(sin(seed*12.9898)*43758.5453)*80.-40.,0,fract(sin(seed*78.233)*23421.631)*80.-40.);centre.x+=mod(weather.x*2.8+seed,80.)-40.;centre.y=camera.y+18.-mod(weather.x*24.+seed*3.71,36.);vec3 c=vec3((v==1||v==2||v==4)?1.:-1.,(v==2||v==4||v==5)?1.:-1.,0);vec3 cameraRight=vec3(cos(angle.x),0,-sin(angle.x));world=centre+cameraRight*c.x*.016+vec3(c.y*.04,c.y*.5,0);colour=vec3(.58,.69,.75);effectAlpha=weather.z*.38;if(weather.z<.015||tactical!=0||world.y<height(world.xz))world.y=-10000;}
 else if(terrain==8){
  // Geometry follows the live authoritative velocity and lifecycle, never an invented shot.
  int kind=floatBitsToInt(metadata.x);vec3 velocity=vec3(entity.w,roles.x,roles.y);
  float speed=length(velocity);vec3 axis=speed>.0001?velocity/speed:vec3(0,0,1);
  vec3 reference=abs(axis.y)>.95?vec3(1,0,0):vec3(0,1,0);
  vec3 right=normalize(cross(reference,axis)),up=cross(axis,right);
  vec3 c=corners[faces[gl_VertexID%36]];
  float width=kind==3?.24:(kind==4?.045:.10),span=kind==3?.7:(kind==4?1.8:.55);
  world=entity.xyz+right*c.x*width+up*(c.y-1.)*width+axis*(c.z*span-(kind==4?span:0.));
  colour=kind==3?vec3(.24,.27,.29):(kind==4?vec3(1.,.54,.13):vec3(1.,.8,.3));
  if(floatBitsToInt(lifecycle.y)==0||distance(entity.xyz,camera)<4.)world.y=-10000;
 }
 else if(terrain==7){int v=gl_VertexID%6;float t=(v==1||v==2||v==4)?1.:0.;float side=(v==2||v==4||v==5)?1.:-1.;vec3 a=entity.xyz,b=roles.xyz;int kind=floatBitsToInt(roles.w);effectType=kind;effectUV=vec2(t*2.-1.,side);if(kind!=1){float ttl=entity.w;float progress=1.-ttl/(kind==2?.45:2.5);float radius=roles.x*(kind==2?(.15+.65*progress):(.4+.8*progress));vec3 horizontal=vec3(cos(angle.x),0,-sin(angle.x));vec3 vertical=vec3(-sin(angle.x)*sin(angle.y),cos(angle.y),-cos(angle.x)*sin(angle.y));if(tactical!=0){horizontal=vec3(1,0,0);vertical=vec3(0,0,1);radius=max(radius,30.);}world=a+horizontal*effectUV.x*radius+vertical*effectUV.y*radius;world.y+=kind==3?progress*roles.x*.6:(kind==4?(progress*20.-progress*progress*38.):0.);if(kind==4)world+=horizontal*progress*roles.x;colour=kind==4?vec3(.38,.25,.14):(kind==2?vec3(1.,.45+.4*(1.-progress),.08):vec3(.25,.27,.26));effectAlpha=kind==2?(1.-progress)*.85:(1.-progress)*.45;if(ttl<=0)world.y=-10000;}else{vec3 axis=normalize(b-a);vec3 view=normalize(camera-mix(a,b,t));vec3 wing=cross(axis,view);float n=length(wing);wing=n>.001?wing/n:vec3(1,0,0);world=mix(a,b,t)+wing*side*.008;colour=vec3(1,.78,.28)*(.7+.3*clamp(entity.w/.14,0,1));effectAlpha=clamp(entity.w/.14,0,1);if(entity.w<=0||tactical!=0)world.y=-10000;}}
 else if(terrain==3){int owner=floatBitsToInt(entity.z),role=floatBitsToInt(roles.x),connected=floatBitsToInt(roles.y),flags=floatBitsToInt(roles.w); int part=gl_VertexID/36; vec3 scale=part==0?vec3(18,12,18):vec3(3,30,3);if(tactical!=0)scale=part==0?vec3(70,12,70):vec3(8,50,8);vec3 offset=part==0?vec3(0):vec3(0,24,0);world=corners[faces[gl_VertexID%36]]*scale+offset+vec3(entity.x,height(entity.xy)+2,entity.y); colour=owner==0?vec3(.2,.75,1):(owner==1?vec3(1,.28,.16):vec3(.85,.8,.6));if(connected==0)colour*=.65;if((flags&4)!=0)colour=vec3(1,.85,.15);if(role==0&&part==1)colour=vec3(.9,.9,.82);}
 else if(terrain==1){int cell=gl_VertexID/6; int v=gl_VertexID%6; vec2 off=vec2((v==1||v==2||v==4)?1:0,(v==2||v==4||v==5)?1:0); vec2 p=(vec2(cell%128,cell/128)+off)*62.5; world=vec3(p.x,height(p),p.y); colour=mix(vec3(.13,.18,.11),vec3(.28,.29,.16),.5+.5*sin(p.x*.007+p.y*.005));}
 else {world=vec3(0,-10000,0);colour=vec3(0);}

 worldPosition=world;
 vec3 p=world-camera;
 if(tactical!=0){gl_Position=vec4((world.x-4000)/4300,(world.z-4000)/4300,-world.y/1000,1); distanceFog=0;}
 else {float cy=cos(angle.x),sy=sin(angle.x),cp=cos(angle.y),sp=sin(angle.y); vec3 q=vec3(cy*p.x-sy*p.z,p.y,sy*p.x+cy*p.z); q=vec3(q.x,cp*q.y-sp*q.z,sp*q.y+cp*q.z); gl_Position=vec4(q.x*1.05,q.y*1.87,q.z*1.00002-.2,q.z); distanceFog=length(p);}
}
