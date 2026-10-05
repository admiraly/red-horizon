#version 450 core
layout(location=0) in vec4 entity;
layout(location=1) in vec4 roles;
uniform vec3 camera;
uniform vec2 angle;
uniform int terrain;
uniform int tactical;
out vec3 colour;
out float distanceFog;
const vec3 corners[8]=vec3[8](vec3(-1,0,-1),vec3(1,0,-1),vec3(1,2,-1),vec3(-1,2,-1),vec3(-1,0,1),vec3(1,0,1),vec3(1,2,1),vec3(-1,2,1));
const int faces[36]=int[36](0,2,1,0,3,2,4,5,6,4,6,7,0,1,5,0,5,4,3,7,6,3,6,2,0,4,7,0,7,3,1,2,6,1,6,5);
float height(vec2 p){return 15*sin(p.x*.003)*sin(p.y*.002)+5*sin(p.x*.013+p.y*.006);}
void main(){
 if(terrain==2){int v=gl_VertexID%6; int bar=gl_VertexID/6; vec2 c=vec2((v==1||v==2||v==4)?1:-1,(v==2||v==4||v==5)?1:-1); vec2 size=bar==0?vec2(.009,.0015):vec2(.0009,.016); gl_Position=vec4(c*size,0,1); colour=vec3(.9,.95,.86); distanceFog=0; return;}
 vec3 world;
 if(terrain!=0){int cell=gl_VertexID/6; int v=gl_VertexID%6; vec2 off=vec2((v==1||v==2||v==4)?1:0,(v==2||v==4||v==5)?1:0); vec2 p=(vec2(cell%128,cell/128)+off)*62.5; world=vec3(p.x,height(p),p.y); colour=mix(vec3(.13,.18,.11),vec3(.28,.29,.16),.5+.5*sin(p.x*.007+p.y*.005));}
 else {int hp=floatBitsToInt(entity.z); int side=floatBitsToInt(entity.w); int kind=floatBitsToInt(roles.x); vec3 scale=kind==0?vec3(.7,1,.7):(kind==3?vec3(8,1.2,5):vec3(3,1.7,5)); if(tactical!=0)scale=max(scale,vec3(12)); int part=gl_VertexID/36; vec3 offset=vec3(0); if(part==1){offset.y=kind==0?2.0:(kind==3?1.0:3.0); scale=kind==0?vec3(.5,.4,.5):(kind==3?vec3(15,.15,1.5):vec3(1.5,.6,2));} world=corners[faces[gl_VertexID%36]]*scale+offset+vec3(entity.x,height(entity.xy)+(kind==3?90:0),entity.y); if(hp==0)world.y=-10000; colour=side==0?vec3(.16,.55,.85):vec3(.9,.25,.12); colour*=.68+.32*float((gl_VertexID%36)/6)/5.;}
 vec3 p=world-camera;
 if(tactical!=0){gl_Position=vec4((world.x-4000)/4300,(world.z-4000)/4300,-world.y/1000,1); distanceFog=0;}
 else {float cy=cos(angle.x),sy=sin(angle.x),cp=cos(angle.y),sp=sin(angle.y); vec3 q=vec3(cy*p.x-sy*p.z,p.y,sy*p.x+cy*p.z); q=vec3(q.x,cp*q.y-sp*q.z,sp*q.y+cp*q.z); gl_Position=vec4(q.x*1.05,q.y*1.87,q.z*1.00002-.2,q.z); distanceFog=length(p);}
}
